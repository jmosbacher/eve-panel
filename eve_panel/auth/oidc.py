import base64

import panel as pn
import param
import pkg_resources

import httpx
import webbrowser
import time
import secrets
import getpass
import authlib
from authlib import jose
from authlib.jose.rfc7517.models import KeySet

from contextlib import contextmanager, asynccontextmanager

from eve_panel import config


class OidcKeySet(param.Parameterized):
    oauth_domain = param.String(config.OAUTH_DOMAIN)
    cert_path = param.String(config.OAUTH_CERT_PATH)

    _keyset = param.ClassSelector(KeySet, default=KeySet({}))

    _keys_timestamp = param.Number(0)
    _keys_ttl = param.Number(300)

    def fetch_keys(self, headers={}):
        with httpx.Client(base_url=self.oauth_domain, headers=headers) as client:
            r = client.get(self.cert_path)
            r.raise_for_status()
        keys = r.json()
        self._keyset = jose.JsonWebKey.import_key_set(keys)

    def extract_claims(self, token):
        header_str = authlib.common.encoding.urlsafe_b64decode(token.split(".")[0].encode()).decode('utf-8')
        header = authlib.common.encoding.json_loads(header_str)
        key = self.find_by_kid(header["kid"])
        return jose.jwt.decode(token, key)

    def extract_verified_claims(self, token, options={}):
        try:
            claims = self.extract_claims(token)
            claims.options = options
            claims.validate()
            return claims
            
        except Exception as e:
            logger.error(f"Exception raised while validating claims: {e}")
            return jose.JWTClaims("", "")

    def validate_claims(self, token, **required_claims):
        options = {k: {"value": v, "essential": True} for k,v in required_claims.items()}
        claims = self.extract_verified_claims(token, options)
        claims.validate()

    def find_by_kid(self, kid):
        if kid not in self._keyset.keys:
            self.fetch_keys()
        return self._keyset.find_by_kid(kid)

    def __getitem__(self, kid):
        return self.find_by_kid(kid)



class OidcToken(param.Parameterized):
    client_id = param.String()
    access_token = param.String()
    id_token = param.String()
    refresh_token = param.String()
    expires = param.Number()
    scope = param.String()
    token_type = param.String("Bearer")

    @property
    def claims(self):
        claims = self.extract_claims(self.access_token)
        try:
            claims.validate()
        except:
            return {}
        return dict(claims)

    @property
    def expired(self):
        return time.time()>self.expires

    @classmethod
    def from_file(cls, path):
        with open(path, "r") as f:
            data = json.load(f)
        return cls(**data)

    def to_dict(self):
        return {k:v for k,v in self.param.get_param_values() if not k.startswith("_")}
        
    def to_file(self, path):
        with open(path, "w") as f:
            json.dump(self.to_dict(), f)

    def refresh_token(self, oauth_domain, oauth_token_path, rtoken, headers={}):
        with httpx.Client(base_url=oauth_domain, headers=headers) as client:
            r = client.post(
                oauth_token_path,
            headers={"content-type":"application/x-www-form-urlencoded"},
            data={
                "grant_type": "refresh_token",
                "refresh_token": rtoken,
                "client_id": self.client_id,
            }
            )
            r.raise_for_status()
            params = r.json()
            params["expires"] = time.time() + params.pop("expires_in", 1e6)
            self.set_param(**params)           
        

class OidcAuthFlow(param.Parameterized):
    client_id = param.String()
    device_code = param.String()
    user_code = param.String()
    verification_uri = param.String()
    expires = param.Number()
    interval = param.Number(5)
    verification_uri_complete = param.String()
    
    def request_token(self, oauth_domain, oauth_code_path, client_id, scope, audience, headers={}):
        with httpx.Client(base_url=oauth_domain, headers=headers) as client:
            r = client.post(
                oauth_code_path,
                data={
                    "client_id": client_id,
                    "scope": scope,
                    "audience": audience,
                    },
                headers={"content-type": "application/x-www-form-urlencoded"})
            r.raise_for_status()
        self.client_id = client_id
        params = r.json()
        params["expires"] = time.time() + params.pop("expires_in", 1)
        for k,v in params.items():
            if hasattr(self, k):
                setattr(self, k, v)

    def fetch_token(self, oauth_domain, oauth_token_path, headers={}):
        with httpx.Client(base_url=oauth_domain, headers=headers) as client:
            r = client.post(
                oauth_token_path,
            headers={"content-type":"application/x-www-form-urlencoded"},
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": self.device_code,
                "client_id": self.client_id,
            }
            )
            r.raise_for_status()
            params = r.json()
            params["expires"] = time.time() + params.pop("expires_in", 1e6)
            params["client_id"] = self.client_id
        return OidcToken(**params)
    


    def await_token(self, oauth_domain, oauth_token_path, headers={}):
        while True:
            if time.time()>self.expires:
                raise TimeoutError("Device code hase expired but not yet authorized.")
            try:
                s = self.fetch_token(oauth_domain, oauth_token_path, headers=headers)
                return s
            except:
                time.sleep(self.interval)

    def perform(self, oauth_domain, oauth_code_path, oauth_token_path,
                 client_id, scope, audience, headers={}, open_browser=False, print_url=False):
        self.request_token(oauth_domain, oauth_code_path, client_id, scope, audience, headers=headers)
        if print_url:
            print(f"Authorization URL: {self.verification_uri_complete}")
        if open_browser:
            webbrowser.open(self.verification_uri_complete)        
        return self.await_token(oauth_domain, oauth_token_path, headers=headers)
        



class OidcSession(param.Parameterized):

    message = param.String("")
    _gui = None
    _cb = None

    oauth_domain = param.String(config.OAUTH_DOMAIN)
    oauth_code_path = param.String(config.OAUTH_CODE_PATH)
    oauth_token_path = param.String(config.OAUTH_TOKEN_PATH)

    client_id = param.String(config.DEFAULT_CLIENT_ID) 
    scopes = param.List([])
    audience = param.String(config.DEFAULT_AUDIENCE)

    flow = param.ClassSelector(OidcAuthFlow, default=OidcAuthFlow())
    keyset = param.ClassSelector(OidcKeySet, default=certs)
    token = param.ClassSelector(OidcToken, default=None)
    state = param.Selector(["Disconnected", "Logged in", "Awaiting token", "Checking token ready", "Token expired"],
                             default="Disconnected")

    @property
    def scope(self):
        scopes = set(config.DEFAULT_SCOPE.split(" ") + self.scopes)
        return " ".join(scopes)

    def login(self, open_browser=False, print_url=False, extra_headers={}):
        self.token = self.flow.perform(self.oauth_domain, self.oauth_code_path, self.oauth_token_path, 
                                        self.client_id, self.scope, self.audience, headers=extra_headers,
                                      open_browser=open_browser, print_url=print_url)
        if self.token:
            self.state = "Logged in"

    def request_token(self,  extra_headers={}):
        
        self.flow.request_token(self.oauth_domain, self.oauth_code_path, 
                                self.client_id, self.scope, self.audience, headers=extra_headers)
        self.state = "Awaiting token"

    def token_ready(self, extra_headers={}):
        if self.token is None:
            try:
                self.token = self.flow.fetch_token(self.oauth_domain,
                                         self.oauth_token_path, headers=extra_headers)
                self.state = "Logged in"
                return True
            except:
                pass
        return False
    
    def refresh_token(self, extra_headers={}):
        self.token = self.flow.refresh_token(self.oauth_domain, self.oauth_token_path, 
                                             self.token.refresh_token, headers=extra_headers)

    def logged_in(self):
        if self.token is None: 
            return False
        if self.token.expired:
            return False
        return True

    @property
    def id_token(self):
        return self.token.id_token

    @property
    def access_token(self):
        return self.token.access_token

    @property
    def profile(self):
        claims = self.keyset.extract_verified_claims(self.id_token)
        return {k:v for k,v in claims.items() if k not in claims.REGISTERED_CLAIMS}
    
    @property
    def claims(self):
        claims = self.keyset.extract_verified_claims(self.access_token)
        return {k:v for k,v in claims.items() if k in claims.REGISTERED_CLAIMS}

    @property
    def extra_claims(self):
        claims = self.keyset.extract_verified_claims(self.access_token)
        return {k:v for k,v in claims.items() if k not in claims.REGISTERED_CLAIMS}

    @property
    def permissions(self):
        claims = self.keyset.extract_verified_claims(self.access_token)
        return claims.get("permissions", [])

    @contextmanager
    def Client(self, *args, **kwargs):
        kwargs["headers"] = kwargs.get("headers", {})
        kwargs["headers"]["Authorization"] = f"Bearer {self.access_token}"
        
        client = httpx.Client(*args, **kwargs)
        try:
            yield client
        finally:
            client.close()

    @asynccontextmanager
    async def AsyncClient(self, *args, **kwargs ):
        kwargs["headers"] = kwargs.get("headers", {})
        kwargs["headers"]["Authorization"] = f"Bearer {self.access_token}"
        client = httpx.AsyncClient(*args, **kwargs)
        try:
            yield client
        finally:
            await client.aclose()

    def authorize(self):
        webbrowser.open(self.flow.verification_uri_complete)
        

    @property
    def gui(self):
        if self._gui is None:
            self._gui = pn.panel(self._make_gui)
        return self._gui

    def await_token_cb(self):
        if self.token_ready() and self.token:
            self._cb.stop()
        
    def login_requested(self, event):
        try:
            self.request_token()
            logger.info("Sent request...")
            self._cb = pn.state.add_periodic_callback(self.await_token_cb,
                                                    1000*self.flow.interval,
                                                    timeout=1000*max(1, int(self.flow.expires-time.time())))
        except Exception as e:
            logging.error(e)
            print(e)

    def logged_in_gui(self):
        profile = self.profile
        details = pn.Row(
            pn.pane.PNG(profile.get("picture", config.DEFAULT_AVATAR), width=60, height=60),
            pn.widgets.TextInput(name='Name', value=profile.get("name", "Unknown"), disabled=True, height=35),
            pn.widgets.TextInput(name='Email', value=profile.get("email", "Unknown"), disabled=True, height=35),
            
            height=70
        )
        token = pn.widgets.input.TextAreaInput(name='Access token', value=self.access_token, width=700, height=100)
        
        token_props = pn.Row(
            pn.widgets.TextInput(name='Scope', value=self.token.scope, disabled=True, height=35),
            pn.widgets.DatetimeInput(disabled=True, name="Expiration date",
                         value=datetime.utcfromtimestamp(self.token.expires)),
            
            width=700,
        )
        return pn.Column(
                    details,
                    token,
                    token_props,
                    height=300,
                    width=700)

    def awaiting_token_gui(self):
        return pn.Column(url_link_button(self.flow.verification_uri_complete))
    
    def token_expired_gui(self):
        refresh = pn.widgets.Button(name="Renew", align="end")
        refresh.on_click(lambda e: self.refresh_token())
        return refresh

    @param.depends("state")
    def _make_gui(self):
        status = pn.indicators.BooleanStatus(width=15, height=15, value=True, color="danger")
        header = pn.Row(status, f"Status: {self.state}.")
        panel = pn.Column(header)
        if self.state == "Logged in":
            status.color = "success"
            panel.append(self.logged_in_gui())
            
        elif self.state == "Awaiting token":
            status.color = "primary"
            panel.append(self.awaiting_token_gui())
        else:
            login = pn.widgets.Button(name="Login", button_type='primary', width=30)
            login.on_click(self.login_requested)
            panel.append(login)
        return panel

    def _repr_mimebundle_(self, include=None, exclude=None):
        return self.gui._repr_mimebundle_(include=include, exclude=exclude)

