
import param
import panel as pn
from collections import defaultdict
from .eve_model import EveModelBase
from .resource import EveResource
from .http_client import DEFAULT_HTTP_CLIENT, EveHttpClient
from . import settings


class EveDomain(EveModelBase):
    name = param.String("EveDomain")
    _http_client = param.ClassSelector(EveHttpClient, precedence=-1)
    _selected = param.Selector(label="", default=None, allow_None=True)
    
    @classmethod
    def from_domain_def(cls, domain_def, domain_name="EveApp", http_client=None, sort_by_url=False):
        if http_client is None:
            http_client = DEFAULT_HTTP_CLIENT()
        if sort_by_url:
            domain_def = {v["url"]: v for v in domain_def.values()}
    
        sub_domains = defaultdict(dict)
        params = {}
        kwargs = {}
        for url, resource_def in sorted(domain_def.items(), key=lambda x: len(x[0])):
            sub_url, _, rest = url.partition("/")
            if rest:
                sub_domains[sub_url][rest] = resource_def
            else:
                resource = EveResource.from_resource_def(resource_def, url, http_client=http_client)
                params[sub_url] = param.ClassSelector(resource.__class__, default=resource, constant=True)
                kwargs[sub_url] = resource
        for url, domain_def in sub_domains.items():
            if url in params:
                for sub_url, resource_def in domain_def.items():
                    resource = EveResource.from_resource_def(resource_def, url, http_client=http_client)
                    kwargs[url+"_"+sub_url] = resource
                    params[url+"_"+sub_url] = param.ClassSelector(resource.__class__, default=resource, constant=True)
            else:
                sub_domain = EveDomain.from_domain_def(domain_def, url, http_client=http_client)
                kwargs[url] = sub_domain
                params[url] = param.ClassSelector(EveDomain, default=sub_domain, constant=True)
        
        klass = type(domain_name+"_domain", (cls,), params)
        instance = klass(name=domain_name, _http_client=http_client, **kwargs)
        instance.param._selected.objects = [""]+ list(params)
        instance._selected = ""
        return instance

    @param.depends("_selected")
    def sub_panel(self):
        if self._selected is None or self._selected=="":
            return pn.Column(height=200, width=int(settings.GUI_WIDTH))
        return getattr(self, self._selected).panel

    def sub_panel_view(self, name):
        def make_panel():
            panel = getattr(self, name).panel(show_client=False)
            return panel
        return make_panel

    def make_panel(self, show_client=True, tabs_location='above'):
        tabs = [(k.upper().replace("_", " "), getattr(self, k).make_panel(show_client=False, tabs_location="above")) for k,v in self.param.objects().items()
                 if isinstance(v, param.ClassSelector) and v.class_ in (EveDomain, EveResource)]
        tabs.sort(key=lambda x:len(x[0]))
        view = pn.Tabs(*tabs, dynamic=True, tabs_location=tabs_location)
        if show_client:
            view.append(("Settings", self._http_client.panel))
        
        return view

    def set_token(self, token):
        self._http_client.set_token(token)

    def __dir__(self):
        return list(self.params())
