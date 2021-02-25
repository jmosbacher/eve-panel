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
from .session import DEFAULT_SESSION_CLASS, EveSessionBase
from .settings import config as settings
from .resource import EveResource


class EveClient(EveModelBase):
    name = param.String("EveClient", doc="Human readable name of the client")
    session = param.ClassSelector(EveSessionBase, constant=True, precedence=-1)

    @classmethod
    def from_domain_def(cls,
                        domain_def,
                        name="EveApp",
                        session=None,
                        auth_scheme=None,
                        servers={},
                        sort_by_url=False):
    
        if session is None:
            session = DEFAULT_SESSION_CLASS(known_servers=servers, auth_scheme=auth_scheme)

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
                    resource_def, url, session=session)
                params[sub_url] = param.ClassSelector(resource.__class__,
                                                      default=resource,
                                                      constant=True)
                kwargs[sub_url] = resource
        for url, domain_def in sub_domains.items():
            if url in params:
                for sub_url, resource_def in domain_def.items():
                    resource = EveResource.from_resource_def(
                        resource_def, url, session=session)
                    kwargs[url + "_" + sub_url] = resource
                    params[url + "_" + sub_url] = param.ClassSelector(
                        resource.__class__, default=resource, constant=True)
            else:
                sub_domain = EveClient.from_domain_def(domain_def,
                                                       url,
                                                       session=session)
                kwargs[url] = sub_domain
                params[url] = param.ClassSelector(EveClient,
                                                  default=sub_domain,
                                                  constant=True)

        klass = type(name.title() + "Client", (cls, ), params)
        instance = klass(name=name, session=session, **kwargs)
        return instance

    @classmethod
    def from_app(cls, app, **kwargs):
        domain_def = app.config["DOMAIN"]
        instance = cls.from_domain_def(domain_def=domain_def, **kwargs)
        return instance
        
    @property
    def logged_in(self):
        return self.session.logged_in
    
    def login(self, *args, **kwargs):
        return self.session.login(*args, **kwargs)

    def logout(self):
        return self.session.logout()

    @property
    def resources(self):
        return {k:v for k, v in self.param.get_param_values() if isinstance(v, EveResource)}
    
    @property
    def sub_resources(self):
        return {k:v for k, v in self.param.get_param_values() if isinstance(v, EveClient)}

    @property
    def resource_tree(self):
        return self.collect_resource_tree(False)

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
            tabs = [("Session", self.session.panel())] + tabs
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
        self.session.set_credentials(token=token)
    
    def set_auth(self, name):
        self.session.set_auth(name)

    def set_credentials(self, **credentials):
        self.session.set_credentials(**credentials)

    def set_server_url(self, **kwargs):
        self.session.set_server_url(**kwargs)

    def get_server_url(self, name):
        self.session.get_server_url(name)

    def select_server(self, name=None):
        self.session.select_server(name)

    @property    
    def servers(self):
        return self.session.known_servers

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
    
