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
__version__ = '0.3.5'

import panel as pn

from .auth import EveAuthBase
from .domain import EveDomain
from .eve_client import EveClient
from .item import EveItem
from .resource import EveResource
from .utils import from_app_config
from .menu import Menu, css
from .web_client import EveWebClient


def extension():
   pn.extension('ace')
   pn.config.raw_css.append(css)
   try:
      import holoviews as hv
      hv.extension('bokeh')
   except ImportError:
      print("Cannot import holoviews, plotting will not work.")

notebook = output_notebook = extension