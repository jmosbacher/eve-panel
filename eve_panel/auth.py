
"""
auth module
====================================
Authentication and Authorization handling
"""

import base64

import panel as pn
import param
import pkg_resources

import httpx
import webbrowser
import time
import secrets
from .eve_model import EveModelBase
from . import settings

class EveAuthBase(EveModelBase):
    """Base class for Eve authentication scheme

    Inheritance:
        param.Parameterized:

    """

    def get_headers(self):
        """Generate auth headers for HTTP requests.

        Returns:
            dict: Auth related headers to be included in all requests.
        """
        return {}

    def login(self):
        """perform any actions required to aquire credentials.

        Returns:
            bool: whether login was successful
        """
        return True

    def set_token(self, token):
        """Set the access token manually.

        Args:
            token ([type]): [description]
        """
        self.token = token

    def credentials_view(self):
        return pn.Row()

class EveBasicAuth(EveAuthBase):
    """
    Support for eve basic auth.

    Inheritance:
        EveAuthBase:

    """
    
    username = param.String(precedence=1, doc="Basic auth username")
    password = param.String(precedence=2, doc="Basic auth password")
    token = param.ClassSelector(bytes, default=b"", doc="Basic auth token")

    def login(self):
        if not self.token:
            self.token = base64.b64encode(
                f"{self.username}:{self.password}".encode())
        return True

    def get_headers(self):
        self.login()
        return {"Authorization": f"Basic {self.token}"}

    def make_panel(self):
        return pn.Param(self.param,
                        max_width=self.max_width,
                        max_height=self.max_height,
                        sizing_mode=self.sizing_mode,
                        parameters=["username", "password"],
                        widgets={"password": pn.widgets.PasswordInput})

    def credentials_view(self):
        return pn.Param(self.param,
                        parameters=["username", "password"],
                        widgets={"password": pn.widgets.PasswordInput},
                        max_width=self.max_width,
                        max_height=self.max_height,
                        sizing_mode=self.sizing_mode,
                        default_layout=pn.Row)

class EveBearerAuth(EveAuthBase):
    """
    Support for Eve bearer auth.

    Inheritance:
        EveAuthBase:

    """
    token = param.String(doc="Beaer token")

    def get_headers(self):
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        else:
            return {}

    def login(self):
        return bool(self.token)

    def make_panel(self):
        return pn.panel(self.param.token,
                        max_width=self.max_width,
                        max_height=self.max_height,
                        sizing_mode=self.sizing_mode,
        )

    def credentials_view(self):
        return self.panel()

class Oauth2DeviceFlow(EveAuthBase):
    auth_server_uri = param.String(
        label="Authentication server",
        default=None,
        regex=r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))")
    code_request_path = param.String(default="code/", label="Code request path")
    token_request_path = param.String(default="token/",label="Token request path")
    verification_path = param.String(default="authorize/",label="Verification path")
    extra_headers = param.Dict(label="Extra headers")
    client_id = param.String(default=secrets.token_urlsafe(12), label="Client ID")
    device_code = param.String()
    user_code = param.String()
    token = param.String()
    
    _cb = param.Parameter(default=None)
    
    def get_client(self):
        return httpx.Client(base_url=self.auth_server_uri, headers=self.extra_headers)
    
    @property
    def authorize_url(self):
        return f"{self.auth_server_uri.strip('/')}/{self.verification_path.strip('/')}?user_code={self.user_code}"
    
    def initiate_flow(self):
        data = {}
        with self.get_client() as client:
            try:
                resp = client.post(self.code_request_path,
                                    data={"client_id": self.client_id,})
                data = resp.json()
            except:
                pass
        self.device_code = data.get("device_code", "")
        self.user_code = data.get("user_code", "")
        interval = data.get("interval", 3)
        timeout = data.get("expires_in", 300)
        if not self.user_code:
            return
        if not self.device_code:
            return
        if self._cb is not None:
            self._cb.stop()
        self._cb = pn.state.add_periodic_callback(self.callback,
                                                period=interval*1000,
                                                count=int(timeout/interval)+1,
                                                )
        
    def authorize_local(self):
        return webbrowser.open(self.authorize_url)
    
    def authorize_link(self):
        html_pane = pn.pane.HTML(f"""
        <a id="log-in-link" class="nav-link" href="{self.authorize_url}" target="_blank">
         Authorize 
        </a>""",
        style={"cursor": "pointer",
                "border": "1px solid #ddd",
                "border-radius": "4px",
                "padding": "5px",})
        return html_pane
    
    def await_token(self):
        with self.get_client() as client:
            for _ in range(int(self.timeout/self.interval)+1):
                data = {}
                try:
                    resp = client.post(self.token_request_path, 
                                      data={"client_id": self.client_id,
                                           "device_code": self.device_code,})
                    data = resp.json()
                except:
                    pass
                token = data.get("access_token", "")
                if token:
                    break
                time.sleep(self.interval)
        return token

    def check_token(self):
        data = {}
        with self.get_client() as client:
            try:
                resp = client.post(self.token_request_path, 
                                  data={"client_id": self.client_id,
                                       "device_code": self.device_code,})
                data = resp.json()
            except:
                pass
        return data.get("access_token", "")
    
    def callback(self):
        token = self.check_token()
        if token and self._cb is not None:
            self.token = token
            self._cb.stop() 
            self._cb = None
            
    @param.depends("_cb", "token")            
    def credentials_view(self):
        init_flow_button = pn.widgets.Button(name="Generate",
                                             button_type="primary",
                                            width=70)
        init_flow_button.on_click(lambda event: self.initiate_flow())
        params = pn.Param(self.param,parameters=["token", "auth_server_uri", "client_id"],
                            widgets={"token": {"type":pn.widgets.TextAreaInput, 
                                               "width":300}},
                            max_width=300,
                            show_label=False,
                            sizing_mode="stretch_width")
        buttons = pn.Row(init_flow_button)
        if self._cb is not None:
            buttons.append(self.authorize_link())
            buttons.append(pn.indicators.LoadingSpinner(value=True, width=20, height=20))
        return pn.Column(params, buttons, sizing_mode="stretch_width", width=300)
    
    def perform_flow(self):
        self.initiate_flow()
        return pn.Column(self.view)
        
    def get_headers(self):
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        else:
            return {}
        
    def make_panel(self):
        # config = ["auth_server_uri", "client_id"]
        # advanced = ["code_request_path", "token_request_path",
        #          "verification_path", "extra_headers",]
        # tabs = pn.Tabs(
        #     ("settings", pn.Param(self.param, parameters=config)),
        #     ("Credentials", self.credentials_view),
        # )
        return pn.panel(self.credentials_view)
    
    def __getstate__(self):
        state = super().__getstate__()
        state.pop("_cb", None)
        return state


AUTH_CLASSES = {
    "Basic": EveBasicAuth,
    "Bearer": EveBearerAuth,
    "Oauth2 Device Flow": Oauth2DeviceFlow,
}



class AuthSelector(EveAuthBase):
    """
    Allows selecting from available authentication schemes
    """

    auth_options = {k: v()
                    for k, v in AUTH_CLASSES.items()
                    }  #[v() for v in AUTH_CLASSES.values()]

    _auth_object = param.ObjectSelector(
        default=auth_options[list(auth_options)[0]],
        objects=auth_options,
        label="Authentication")
    # _auth = param.ClassSelector(EveAuthBase, default=EveBasicAuth())
    @property
    def token(self):
        return getattr(self._auth_object, "token", "")

    @token.setter
    def token(self, val):
        setattr(self._auth_object, "token", val)

    def login(self):
        return self._auth_object.login()

    def get_headers(self):
        return self._auth_object.get_headers()

    @param.depends("_auth_object")
    def auth_view(self):
        if self._auth_object is None or not hasattr(self._auth_object,
                                                    "panel"):
            return pn.Column(max_width=self.max_width,
                            max_height=self.max_height,
                            sizing_mode=self.sizing_mode,)

        return self._auth_object.panel()

    @param.depends("_auth_object")
    def credentials_view(self):
        if self._auth_object is None or not hasattr(self._auth_object,
                                                    "credentials_view"):
            return pn.Row("# No Authentication defined.")

        return self._auth_object.credentials_view()

    def set_auth_by_name(self, name):
        self._auth_object = self.param._auth_object.names[name]

    def panel(self):
        return pn.Column(self.param._auth_object,
                         self.auth_view, 
                        max_width=self.max_width,
                        max_height=self.max_height,
                        sizing_mode=self.sizing_mode,)

    def __init__(self, **params):
        super().__init__(**params)
        for entry_point in pkg_resources.iter_entry_points('eve_panel.auth'):
            auth_class = entry_point.load()
            if issubclass(auth_class, EveAuthBase):
                AUTH_CLASSES[entry_point.name] = auth_class
        auth_options = {k: v() for k, v in AUTH_CLASSES.items()}
        self.param._auth_object.objects = list(auth_options.values())
        self.param._auth_object.names = auth_options
        self._auth_object = auth_options[list(auth_options)[0]]
