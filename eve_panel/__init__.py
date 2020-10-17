"""Top-level package for Eve-Panel."""
from .client import EveApiClient
from .domain import EveDomain
from .resource import EveResource
from .item import EveItem 
import panel as pn
pn.extension()

__author__ = """Yossi Mosbacher"""
__email__ = 'joe.mosbacher@gmail.com'
__version__ = '0.1.0'
