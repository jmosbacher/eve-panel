import param
import httpx
import webbrowser
import time
import secrets
from contextlib import contextmanager, asynccontextmanager
import json
import panel as pn

from .eve_model import EveModelBase
from .settings import config as settings
from .auth import EveAuthBase, AUTH_CLASSES, DEFAULT_AUTH
from .exceptions import ServerError, AuthError
from .utils import is_valid_url


class EveSessionBase(EveModelBase):
    EXTRA_HEADERS = {
        "Accept": "application/json",
        # "Content-Type": "application/json",
    }

    log = param.String()

    auth_schemes = param.Dict(default={}, precedence=-1)
    auth_scheme = param.Selector(default=DEFAULT_AUTH, objects=list(AUTH_CLASSES))

    # selected_server = param.String("default")

    known_servers = param.Dict({})

    server_url = param.Selector(objects={"localhost": "http://localhost"})

    """Base class for Eve authentication scheme

    Inheritance:
        param.Parameterized:

    """

    def __init__(self, **params):
        auth_schemes = {name: klass() for name, klass in AUTH_CLASSES.items()}
        params["auth_schemes"] = params.get("auth_schemes", auth_schemes)
        super().__init__(**params)
        self.update_server_url_options()
        

    @classmethod
    def from_json(cls, obj):
        raise NotImplementedError
    
    @classmethod
    def from_file(cls, file_):
        raise NotImplementedError

    def update_server_url_options(self):
        self.param.server_url.names = self.known_servers
        self.param.server_url.objects = list(self.known_servers.values())
        
    @property
    def app(self):
        return None

    @property
    def auth(self):
        return self.auth_schemes.get(self.auth_scheme)
        
    def to_json(self):
        raise NotImplementedError

    def to_file(self):
        raise NotImplementedError

    def login(self, *args, **kwargs):
        """perform any actions required to aquire credentials.

        Returns:
            bool: whether login was successful
        """
        return self.auth.login(*args, **kwargs)

    def logout(self):
        return self.auth.logout()

    @property
    def logged_in(self):
        return self.auth.logged_in

    def set_credentials(self, *args, **kwargs):
        """Set the credentials manually.

        Args:
            token ([type]): [description]
        """
        self.auth.set_credentials(*args, **kwargs)

    def get_credentials(self):
        self.auth.get_credentials()

    def set_server_url(self, **kwargs):
        self.known_servers.update({name: url for name, url in kwargs.items() if is_valid_url(url)})
        self.update_server_url_options()

    def get_server_url(self, name):
        return self.known_servers.get(name, None)

    def select_server(self, name=None):
        self.update_server_url_options()
        try:
            while name not in self.known_servers:
                try:
                    name = list(self.known_servers)[int(name)]
                    break
                except:
                    pass
                options = "\n".join(["Known servers:"]+[f"{i}) {k} ({v})" for i, (k,v) 
                                                        in enumerate(self.known_servers.items())])
                name = input(options+"\nServer name: ")
            if name in self.known_servers:
                self.server_url = self.known_servers[name]
        except KeyboardInterrupt:
            pass
    
    @property
    def auth_options(self):
        return list(self.auth_schemes)

    def set_auth(self, auth_name):
        if auth_name in self.auth_schemes:
            self.auth_scheme = auth_name
        else:
            raise ValueError(f"{auth_name} is not a valid auth option. \n Valid options are: {self.auth_options}")

    @param.depends("auth_scheme")
    def credentials_view(self):
        return pn.Column(self.auth.credentials_view)
    
    def make_panel(self):
        log = pn.Param(self.param.log, 
            widgets={"log": {"type": pn.widgets.TextAreaInput, "disabled": True, "height": 150}},
            sizing_mode="stretch_both")
        server_select = pn.Param(self.param.server_url)
        server_selected = pn.Param(self.param.server_url, 
                            widgets={"server_url": pn.widgets.StaticText}, show_labels=False)
        return pn.Column(server_select, server_selected, 
                        self.param.auth_scheme,
                        self.credentials_view, log)

    def auth_view(self):
        return pn.Row()
    
    def log_error(self, msg):
        self.log = "\n".join([str(msg), self.log])
        lines = self.log.split("\n")
        if len(lines)> settings.MAX_LOG_SIZE:
            self.log = "\n".join(lines[:settings.MAX_LOG_SIZE])

    def clear_messages(self):
        pass

    @property
    def headers(self):
        h = dict(self.auth.get_headers())
        h.update(self.EXTRA_HEADERS)
        return h

    def check_errors(self, response):
        try:
            response.raise_for_status()
            if response.text:
                r = response.json()
                if "_status" in r and r["_status"]=="ERR":
                    raise ServerError(r["_error"]["code"], r["_error"]["message"])
        except Exception as e:
            if settings.IGNORE_ERRORS:
                self.log_error(e)
            else:
                raise e

    def response_hook(self, response):
        self.check_errors(response)
            
    async def response_hook_async(self, response):
        self.check_errors(response)
        
    def get_client_kwargs(self, headers={}, **kwargs):
        if not self.logged_in and not settings.IGNORE_ERRORS:
            raise AuthError("Not logged in.")
            # try:
            #     self.login()
            # except:
            #     if not settings.IGNORE_ERRORS:
            #         raise AuthError("Cannot log in.")
        timeout = kwargs.get("timeout", httpx.Timeout(settings.DEFAULT_TIMEOUT, 
                                        connect=settings.DEFAULT_TIMEOUT*6))
        user_headers = dict(headers)
        headers = self.headers
        headers.update(user_headers)
        kwargs["headers"] = headers
        kwargs["base_url"] = kwargs.get("base_url", self.server_url)
        kwargs["app"] = kwargs.get("app", self.app)
        kwargs["timeout"] = timeout
        return kwargs
    
    @contextmanager
    def Client(self, *args, **kwargs):
        kwargs = self.get_client_kwargs(**kwargs)
        client = httpx.Client(*args, **kwargs)
        client.event_hooks["response"] = [self.response_hook]
        try:
            yield client
        finally:
            client.close()

    @asynccontextmanager
    async def AsyncClient(self, *args, **kwargs ):
        kwargs = self.get_client_kwargs(**kwargs)
        client = httpx.AsyncClient(*args, **kwargs)
        client.event_hooks["response"] = [self.response_hook_async]
        try:
            yield client
        finally:
            await client.aclose()
    
    def get(self, url, timeout=10, **params):
      with self.Client() as client:
        resp = client.get(url,
                        params=params,
                        timeout=timeout)
        if resp.is_error:
            self.log_error(resp.text)
            return {}
        else:
            self.clear_messages()
            return resp.json()

    async def get_async(self, url, timeout=10, **params):
      with self.AsyncClient() as client:
        resp = await client.get(url,
                        params=params,
                        timeout=timeout)
        if resp.is_error:
            self.log_error(resp.text)
        else:
            return resp.json()
        return {}

    def post(self, url, data="", json={}, timeout=10, **kwargs):
        with self.Client(headers={"Content-Type": "application/json"}) as client:
            resp = client.post(url,
                                data=data,
                                json=json,
                                timeout=timeout,
                                **kwargs)
            if resp.is_error:
                self.log_error(resp.text)
                return False
            else:
                self.clear_messages()
                return True

    async def post_async(self, url, data="", json={}, timeout=10, **kwargs):
        with self.AsyncClient(headers={"Content-Type": "application/json"}) as client:
            resp = await client.post(url,
                                data=data,
                                json=json,
                                timeout=timeout,
                                **kwargs)
            if resp.is_error:
                self.log_error(resp.text)
                return False
            else:
                self.clear_messages()
                return True

    def put(self, url, data={}, etag=None, timeout=10, headers={}, **kwargs):
        with self.Client(headers={"Content-Type": "application/json"}) as client:
            if etag:
                headers["If-Match"] = etag
            resp = client.put(url,
                                data=data,
                                headers=headers,
                                timeout=timeout,
                                **kwargs)
            if resp.is_error:
                self.log_error(resp.text)
                return False
            else:
                self.clear_messages()
                return True


    def patch(self, url, data, etag=None, timeout=10, headers={}, **kwargs):
        with self.Client(headers={"Content-Type": "application/json"}) as client:
            if etag:
                headers["If-Match"] = etag
            try:
                resp = client.patch(url,
                                    data=data,
                                    headers=headers,
                                    timeout=timeout,
                                    **kwargs)
                if resp.is_error or settings.DEBUG:
                    self.log_error(resp.text)
                    return False
                else:
                    self.clear_messages()
                    return True
            except Exception as e:
                self.log_error(e)

    def delete(self, url, etag="", timeout=10, headers={}):
        with self.Client() as client:
            if etag:
                headers["If-Match"] = etag
            try:
                resp = client.delete(url, headers=headers, timeout=timeout)
                if resp.is_error:
                    self.log_error(resp.text)
                    return False
                else:
                    self.clear_messages()
                    return True
            except Exception as e:
                self.log_error(e)


class EveSession(EveSessionBase):
    pass

class EveSelfServeSession(EveSessionBase):
    app_settings = param.Dict(default=None, allow_None=True)
    _app = None

    @property
    def app(self):
        import eve
        if self._app is None:
            self._app = eve.Eve(settings=self.app_settings)
        return self._app


DEFAULT_SESSION_CLASS = EveSession