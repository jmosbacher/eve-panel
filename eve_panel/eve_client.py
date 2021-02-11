"""
Eve client
====================================
Client for single or multiple Eve APIs.
"""

from pprint import pprint

import eve
import panel as pn
import param
from collections import defaultdict

from .eve_model import EveModelBase
from .http_client import DEFAULT_HTTP_CLIENT, EveHttpClient
from .settings import config as settings
from .resource import EveResource



class EveClient(EveModelBase):
    name = param.String("EveClient", doc="Human readable name of the client")
    _http_client = param.ClassSelector(EveHttpClient, precedence=-1, doc="http client to be used for requests.")

    @classmethod
    def from_domain_def(cls,
                        domain_def,
                        domain_name="EveApp",
                        http_client=None,
                        sort_by_url=False):
        if http_client is None:
            http_client = DEFAULT_HTTP_CLIENT()
        if sort_by_url:
            domain_def = {v["url"]: v for v in domain_def.values()}

        sub_domains = defaultdict(dict)
        params = {}
        kwargs = {}
        for url, resource_def in sorted(domain_def.items(),
                                        key=lambda x: len(x[0])):
            sub_url, _, rest = url.partition("/")
            if rest:
                sub_domains[sub_url][rest] = resource_def
            else:
                resource = EveResource.from_resource_def(
                    resource_def, url, http_client=http_client)
                params[sub_url] = param.ClassSelector(resource.__class__,
                                                      default=resource,
                                                      constant=True)
                kwargs[sub_url] = resource
        for url, domain_def in sub_domains.items():
            if url in params:
                for sub_url, resource_def in domain_def.items():
                    resource = EveResource.from_resource_def(
                        resource_def, url, http_client=http_client)
                    kwargs[url + "_" + sub_url] = resource
                    params[url + "_" + sub_url] = param.ClassSelector(
                        resource.__class__, default=resource, constant=True)
            else:
                sub_domain = EveClient.from_domain_def(domain_def,
                                                       url,
                                                       http_client=http_client)
                kwargs[url] = sub_domain
                params[url] = param.ClassSelector(EveClient,
                                                  default=sub_domain,
                                                  constant=True)

        klass = type(domain_name + "_domain", (cls, ), params)
        instance = klass(name=domain_name, _http_client=http_client, **kwargs)
        return instance

    @classmethod
    def from_app(cls, app,
                  name="EveClient",
                  sort_by_url=False, 
                  http_client_class=DEFAULT_HTTP_CLIENT , **kwargs):

        settings = app.config
        http_client = http_client_class.from_app_settings(dict(settings))
        instance = cls.from_domain_def(domain_def=settings["DOMAIN"],
                                        domain_name=name,
                                        http_client=http_client,
                                        sort_by_url=sort_by_url,
                )
        return instance

    def make_panel(self, show_client=True, tabs_location='above'):
        tabs = [
            (k.upper().replace("_", " "),
             getattr(self, k).make_panel(show_client=False,
                                         tabs_location="above"))
            for k, v in self.param.objects().items()
            if isinstance(v, param.ClassSelector) and v.class_ in (EveClient,
                                                                   EveResource)
        ]
        tabs.sort(key=lambda x: len(x[0]))
        if show_client:
            tabs = [("Config", self._http_client.panel)] + tabs
        view = pn.Tabs(*tabs,
                    width=self.max_width-10,
                    max_width=self.max_width,
                    height=self.max_height,
                    sizing_mode=self.sizing_mode,
                    width_policy="max",
                    dynamic=True,
                    tabs_location=tabs_location)
        return view

    def set_token(self, token):
        self._http_client.set_token(token)

    def collect_resource_tree(self, sort=True):
        tree = {}
        for k, v in self.param.get_param_values():
            if isinstance(v, EveClient):
                tree[k] = v.collect_resource_tree()
            elif isinstance(v, EveResource):
                tree[k] = v
        if sort:
            tree = dict(sorted(tree.items(), key=lambda x: len(x[0])))
        return tree

    def __dir__(self):
        return list(self.params())

    def __repr__(self):
        return f"EveClient(name={self.name})"
    
