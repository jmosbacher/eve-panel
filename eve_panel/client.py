import param
import panel as pn
import httpx
import json
from .eve_model import EveModelBase
from .auth import EveAuthBase, AuthSelector
import pkg_resources

AVAILABLE_APPS = {"Remote": lambda: None}

APPS = {}

class EveApiClient(EveModelBase):
    _app_name = param.Selector(default=None, objects=list(AVAILABLE_APPS), allow_None=True)
    api_root = param.String(default="http://localhost:5000", regex=r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))")
    auth = param.ClassSelector(EveAuthBase, default=AuthSelector())
    _log = param.String()
    _busy = param.Boolean(False)

    def __init__(self, **params):
        super().__init__(**params)
        for entry_point in pkg_resources.iter_entry_points('eve_panel.apps'):
            AVAILABLE_APPS[entry_point.name] = entry_point.load()
        self.param._app_name.objects = list(AVAILABLE_APPS)

    @classmethod
    def from_app_config(cls, config, address="http://localhost:5000"):
        api_root = address.strip("/") + "/".join([config["URL_PREFIX"], config["API_VERSION"]]).replace("//","/")
        instance = cls(api_root=api_root)
        return instance
    
    @property
    def app(self):
        app = None
        if self._app_name not in APPS:
            APPS[self._app_name] = AVAILABLE_APPS[self._app_name]()
        return APPS[self._app_name]

    def headers(self):
        headers = self.auth.get_headers()
        headers["accept"] = "application/json"
        return headers
    
    def get(self, url, timeout=10, **params):
        with httpx.Client(app=self.app, base_url=self.api_root) as client:
            self._busy = True
            try:
                resp = client.get(url, params=params, headers=self.headers(), timeout=timeout)
                self._busy = False
                if resp.is_error:
                    self.log_error(resp)
                else:
                    return resp.json()
            except Exception as e:
                self.log_error(e)
            self._busy = False

    def post(self, url, data="", json={}, timeout=10):
        with httpx.Client(app=self.app, base_url=self.api_root) as client:
            self._busy = True
            try:
                resp = client.post(url, data=data, json=json, headers=self.headers(), timeout=timeout)
                self._busy = False
                if resp.is_error:
                    self.log_error(resp)
                    return False
                else:
                    return True
            except Exception as e:
                self.log_error(e)
            self._busy = False

    def put(self, url, data, timeout=10):
        with httpx.Client(app=self.app, base_url=self.api_root) as client:
            self._busy = True
            try:
                resp = client.put(url, data=data, headers=self.headers(), timeout=timeout)
                self._busy = False
                if resp.is_error:
                    self.log_error(resp)
                    return False
                else:
                    return True
            except Exception as e:
                self.log_error(e)
        self._busy = False

    def patch(self, url, data, timeout=10):
        with httpx.Client(app=self.app, base_url=self.api_root) as client:
            self._busy = True
            try:
                resp = client.patch(url, data=data, headers=self.headers(), timeout=timeout)
                self._busy = False
                if resp.is_error:
                    self.log_error(resp)
                    return False
                else:
                    return True
            except Exception as e:
                self.log_error(e)
            self._busy = False

    def delete(self, url, etag, timeout=10):
        with httpx.Client(app=self.app, base_url=self.api_root) as client:
            self._busy = True
            headers = self.headers()
            if etag:
                headers["If-Match"] = etag
            try:
                resp = client.post(url,headers=headers, timeout=timeout)
                self._busy = False
                if resp.is_error:
                    self.log_error(resp)
                    return False
                else:
                    return True
            except Exception as e:
                self.log_error(e)
            self._busy = False

    def log_error(self, resp):
        self._log = str(resp)
            
    def make_panel(self):
        settings = pn.Param(self.param, parameters=["_app_name", "api_root","_log"], width=500, height=150, show_name=False,
                        widgets={"_log": {'type': pn.widgets.TextAreaInput, 'disabled': True, "height":150},})
        return pn.Column(self.auth.panel, settings)
    
    @param.depends("_busy")
    def busy_indicator(self):
        return pn.Param(self.param._busy, width=25,
                    widgets={"_busy": {"type": pn.indicators.LoadingSpinner, "width":20, "height":20}})

def default_client():
    return EveApiClient()

