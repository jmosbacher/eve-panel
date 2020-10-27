
from .client import EveApiClient
from .domain import EveDomain

def from_app_config(name, config, address="http://localhost:5000"):
    client = EveApiClient.from_app_config(config, address=address)
    return EveDomain.from_domain_def(name, config["DOMAIN"], client=client)