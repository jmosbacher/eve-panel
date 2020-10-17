
import param
import panel as pn
from collections import defaultdict
from .eve_model import EveModelBase
from .resource import EveResource
from .client import default_client


class EveDomain(EveModelBase):
    
    @classmethod
    def from_domain_def(cls, domain_name, domain_def, client=None):
        if client is None:
            client = default_client()
        sub_domains = defaultdict(dict)
        params = {}
        for url, resource_def in domain_def.items():
            sub_url, _, rest = url.partition("/")
            if rest:
                sub_domains[sub_url][rest] = resource_def
            else:
                resource = EveResource.from_resource_def(url, resource_def, client=client)
                params[sub_url] = param.ClassSelector(resource.__class__, default=resource,)
        for sub_url, resource_def in sub_domains.items():
            sub_domain = EveDomain.from_domain_def(sub_url, resource_def, client=client)
            params[sub_url] = param.ClassSelector(EveDomain, default=sub_domain,)
        klass = type(domain_name, (cls,), params)
        return klass()

    def __dir__(self):
        return list(self.params())
