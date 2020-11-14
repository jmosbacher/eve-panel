"""
Eve client
====================================
Client for single or multiple Eve APIs.
"""

from pprint import pprint

import eve
import panel as pn
import param

from .domain import EveDomain
from .eve_model import EveModelBase
from .http_client import DEFAULT_HTTP_CLIENT, EveHttpClient


class EveClient(EveModelBase):

    @classmethod
    def from_apps_dict(cls, apps: dict,
                  name="EveClient",
                  sort_by_url=False, 
                  http_client_class=DEFAULT_HTTP_CLIENT , **kwargs):
        params = {}
        for app_name, app in apps.items():
            settings = app.config
            http_client = http_client_class.from_app_settings(dict(settings))
            domain = EveDomain.from_domain_def(domain_def=settings["DOMAIN"],
                                            domain_name=app_name,
                                            http_client=http_client,
                                            sort_by_url=sort_by_url)
            params[app_name] = param.ClassSelector(EveDomain, default=domain, constant=True)
        klass = type(name, (cls,), params)
        return klass(**kwargs)

    @classmethod
    def from_app_settings_dict(cls, settings_dict: dict,
                          sort_by_url=False,
                          name="EveClient", 
                          http_client_class=DEFAULT_HTTP_CLIENT , **kwargs):
        apps = {name: eve.Eve(settings=settings) for name, settings in settings_dict}
        return cls.from_apps_dict(apps, name=name, sort_by_url=sort_by_url, **kwargs)

    @property
    def domains(self):
        return {k: v for k,v in self.param.get_param_values() if isinstance(v, EveDomain)}

    def make_panel(self, show_client=False):
        domains = [(k.replace("_", " ").upper(), v.panel()) for k,v in self.domains.items()]
        if not domains:
            return pn.Column("### No Domains configured.")
        if len(domains)>1:
            return pn.Tabs(*domains,
                 width=self.max_width,
                 height=self.max_height,
                 sizing_mode=self.sizing_mode,                
                 dynamic=True)
        else:
            name, domain = domains[0]
            return pn.Column(f"### {name}",
                             domain,
                             width=self.max_width,
                             max_width=self.max_width,
                             height=self.max_height,
                             sizing_mode=self.sizing_mode,
                             )

    def collect_domain_tree(self):
        return {k: v.collect_resource_tree() for k, v in self.domains.items()}

    def __repr__(self):
        return f"EveClient(name={self.name}, domains={len(self.domains)})"
    
