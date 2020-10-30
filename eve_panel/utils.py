
from .eve_client import EveClient
from .domain import EveDomain

def from_app_config(name, config, address="http://localhost:5000"):
    return EveClient.from_app_settings(config, address=address)
