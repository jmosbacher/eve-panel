
import base64
import panel as pn
import param
import getpass
import logging
import httpx
import webbrowser

from .base import EveAuthBase

logger = logging.getLogger(__name__)


class Oauth2DeviceFlow(EveAuthBase):
    auth_server_uri = param.String(
        label="Authentication server",
        default=None,
        regex=r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))")
    code_request_path = param.String(default="/device/code", label="Code request path")
    token_request_path = param.String(default="token",label="Token request path")
    verification_path = param.String(default="authorize",label="Verification path")
    extra_headers = param.Dict(label="Extra headers")
    client_id = param.String(default="eve_client", label="Client ID")
    notify_email = param.String(default="", label="Notify Email")
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
                                    data={"client_id": self.client_id,
                                    "notify_email": self.notify_email})
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
        
    def authorize(self):
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
                    self.token = token
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
        params = pn.Param(self.param, parameters=["token", "auth_server_uri",
                                                 "client_id","notify_email"],
                            widgets={"token": {"type":pn.widgets.TextAreaInput, 
                                               "width":300}},
                            max_width=300,
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

    def login(self):
        self.initiate_flow()
        self.authorize()
        token = self.await_token()
        return bool(token)

    @property    
    def logged_in(self):
        return bool(token)

    def logout(self):
        self.token = ""
        
    def make_panel(self):
        return pn.panel(self.credentials_view)
    
    def __getstate__(self):
        state = super().__getstate__()
        state.pop("_cb", None)
        return state










