"""
auth module
====================================
Authentication and Authorization handling
"""
import pkg_resources

from .base import EveAuthBase, EveNoAuth
from .basic_auth import EveBasicAuth
from .bearer import EveBearerAuth
from .oauth2 import Oauth2DeviceFlow

AUTH_CLASSES = {
    None: EveNoAuth,
    "Basic": EveBasicAuth,
    "Bearer": EveBearerAuth,
    "Oauth2 Device Flow": Oauth2DeviceFlow,
}

for entry_point in pkg_resources.iter_entry_points('eve_panel.auth'):
    AUTH_CLASSES[entry_point.name] = entry_point.load()

import pkg_resources

DEFAULT_AUTH = None