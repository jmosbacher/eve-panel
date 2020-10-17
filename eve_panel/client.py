import param
import panel as pn
import httpx
import json
from .eve_model import EveModelBase
# from .domain import EveDomain
from .auth import EveClientAuth, EveBearerAuth

class EveApiClient(EveModelBase):
    app = param.Parameter(default=None)
    server_url = param.String(default="http://localhost:5000", regex=r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))")
    auth = param.ClassSelector(EveClientAuth, default=EveBearerAuth())
    # domain = param.ClassSelector(EveDomain)
    _log = param.String()
    
    max_results = param.Integer(default=25, doc="Items per page")
    page = param.Integer(default=1, doc="Page")
    filters = param.Dict(default={}, doc="Filters")
    projection = param.Dict(default={}, doc="Projections")

    prev_page = param.Action(lambda self: self.load_prev_page, label="Previous")
    next_page = param.Action(lambda self: self.load_next_page, label="Next")
    
    @classmethod
    def from_app_config(cls, config, address="http://localhost:5000", self_serve=False):
        server_url = address.strip("/") + "/".join([config["URL_PREFIX"], config["API_VERSION"]]).replace("//","/")
        # domain = EveDomain.from_domain_def(server_url ,config["DOMAIN"])
        app = None
        if self_serve:
            import eve
            app = eve.Eve(config)
        return cls(server_url=server_url, app=app)
       
    def headers(self):
        headers = self.auth.get_headers()
        headers["accept"] = "application/json"
        return headers
    
    def get(self, url, timeout=10, **params):
        with httpx.Client(app=self.app, base_url=self.server_url) as client:
            resp = client.get(url, params=params, headers=self.headers(), timeout=timeout)
            if resp.is_error:
                self.log_error(resp)
            else:
                return resp.json()
            
    def post(self, url, data="", json={}, timeout=10):
        with httpx.Client(app=self.app, base_url=self.server_url) as client:
            resp = client.post(url, data=data, json=json, headers=self.headers(), timeout=timeout)
            if resp.is_error:
                self.log_error(resp)
                return False
            else:
                return True
    
    def put(self, url, data, timeout=10):
        with httpx.Client(app=self.app, base_url=self.server_url) as client:
            resp = client.post(url, data=data, headers=self.headers(), timeout=timeout)
            if resp.is_error:
                self.log_error(resp)
                return False
            else:
                return True
    
    def patch(self):
        pass
    
    def delete(self,):
        pass
    
    def log_error(self, resp):
        self._log = str(resp)
        
    def load_resource(self, resource, **kwargs):
        if isinstance(resource, str):
            resource = getattr(self.domain,resource)
        params = {
            "page": self.page,
            "max_results": self.max_results,
            "filters": json.dumps(self.filters),
            "projection": json.dumps(self.projection),
        }
        data = self.get(resource._resource["url"], params=params, **kwargs)
        if data:
            return data
        else:
            return {"_items": [], '_meta': {'page': page, 'max_results': max_results, 'total': 0}}

    def load_item(self, resource, item_id):
        if isinstance(resource, str):
            resource = getattr(self.domain, resource)

        data = self.get("/".join([resource._resource["url"], item_id]))
        if data:
            return data
        else:
            return {"_id": item_id,}
            
    def panel(self):
        settings = pn.Param(self.param, parameters=["server_url","_log"], width=500, height=150, show_name=False,
                        widgets={"_log": {'type': pn.widgets.TextAreaInput, 'disabled': True, "height":150},})
        return pn.Column(self.auth.panel, settings)
        
def default_client():
    return EveApiClient()