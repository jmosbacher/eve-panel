"""Top-level package for Eve-Panel."""
from .eve_client import EveClient
from .domain import EveDomain
from .resource import EveResource
from .item import EveItem

from .utils import from_app_config

import panel as pn

def notebook():
    return pn.extension()

__author__ = """Yossi Mosbacher"""
__email__ = 'joe.mosbacher@gmail.com'
__version__ = '0.1.0'

