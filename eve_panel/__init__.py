# -*- coding: utf-8 -*-
"""Eve-panel.

A marriage between Eve and Panel.

Example:
    
Todo:


.. _Google Python Style Guide:
   http://google.github.io/styleguide/pyguide.html

"""

__author__ = """Yossi Mosbacher"""
__email__ = 'joe.mosbacher@gmail.com'
__version__ = '0.3.3'

import panel as pn

from .auth import EveAuthBase
from .domain import EveDomain
from .eve_client import EveClient
from .item import EveItem
from .resource import EveResource
from .utils import from_app_config


def notebook():
    """ Load notebook support. """
    return pn.extension()


