
import param
import panel as pn
from collections import defaultdict
from .eve_model import EveModelBase
from .resource import EveResource
from .client import default_client, EveApiClient
from . import settings

class EveDomain(EveModelBase):
    name = param.String("EveDomain")
    _client = param.ClassSelector(EveApiClient, precedence=-1)
    _selected = param.Selector(label="", default=None, allow_None=True)
    
    @classmethod
    def from_domain_def(cls, domain_name, domain_def, client=None):
        if client is None:
            client = default_client()
        sub_domains = defaultdict(dict)
        params = {}
        kwargs = {}
        for url, resource_def in sorted(domain_def.items(), key=lambda x: len(x[0])):
            sub_url, _, rest = url.partition("/")
            if rest:
                sub_domains[sub_url][rest] = resource_def
            else:
                resource = EveResource.from_resource_def(url, resource_def, client=client)
                params[sub_url] = param.ClassSelector(resource.__class__, default=resource, constant=True)
                kwargs[sub_url] = resource
        for url, domain_def in sub_domains.items():
            if url in params:
                for sub_url, resource_def in domain_def.items():
                    resource = EveResource.from_resource_def(url, resource_def, client=client)
                    kwargs[url+"_"+sub_url] = resource
                    params[url+"_"+sub_url] = param.ClassSelector(resource.__class__, default=resource, constant=True)
            else:
                sub_domain = EveDomain.from_domain_def(url, domain_def, client=client)
                kwargs[url] = sub_domain
                params[url] = param.ClassSelector(EveDomain, default=sub_domain, constant=True)
        
        klass = type(domain_name+"_domain", (cls,), params)
        instance = klass(name=domain_name, _client=client, **kwargs)
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
            panel = getattr(self, name).panel(client=False)
            return panel
        return make_panel

    def make_panel(self, client=True, tabs_location='left'):
        tabs = [(k.upper().replace("_", " "), getattr(self, k).make_panel(client=False, tabs_location="above")) for k,v in self.param.objects().items()
                 if isinstance(v, param.ClassSelector) and v.class_ in (EveDomain, EveResource)]

        view = pn.Tabs(*tabs, dynamic=True, tabs_location=tabs_location)
        if client:
            view.append(("Settings", self._client.panel))
        return view

    def set_token(self, token):
        self._client.auth.token = token

    def __dir__(self):
        return list(self.params())
