from .domain import EveDomain
from .eve_client import EveClient


def from_app_config(name, config, address="http://localhost:5000"):
    return EveClient.from_app_settings(config, address=address)
