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
    _http_client = param.ClassSelector(EveHttpClient,
                                       default=DEFAULT_HTTP_CLIENT())
    domain = param.ClassSelector(EveDomain)

    @classmethod
    def from_app(cls, app, name="EveDomain", sort_by_url=False):
        settings = app.config
        # pprint(settings["DOMAIN"])
        http_client = DEFAULT_HTTP_CLIENT.from_app_settings(dict(settings))
        domain = EveDomain.from_domain_def(domain_def=settings["DOMAIN"],
                                           domain_name=name,
                                           http_client=http_client,
                                           sort_by_url=sort_by_url)
        return cls(domain=domain, _http_client=http_client)

    @classmethod
    def from_app_settings(cls, settings, sort_by_url=False):
        app = eve.Eve(settings=settings)
        return cls.from_app(app, sort_by_url=sort_by_url)

    @property
    def db(self):
        return self.domain

    def make_panel(self, show_client=False):
        return self.domain.make_panel(show_client=show_client)

    def set_token(self, token):
        self._http_client.set_token(token)
