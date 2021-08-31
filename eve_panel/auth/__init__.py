"""
auth module
====================================
Authentication and Authorization handling
"""
import pkg_resources
import logging

from .base import EveAuthBase, EveNoAuth
from .basic_auth import EveBasicAuth
from .bearer import EveBearerAuth
from .oauth2 import Oauth2DeviceFlow
from .panel_oauth import EvePanelAuth

log = logging.getLogger(__name__)


AUTH_CLASSES = {
    None: EveNoAuth,
    "Basic": EveBasicAuth,
    "Bearer": EveBearerAuth,
    "Panel": EvePanelAuth,
    "Oauth2 Device Flow": Oauth2DeviceFlow,
}

for entry_point in pkg_resources.iter_entry_points('eve_panel.auth'):
    try:
        AUTH_CLASSES[entry_point.name] = entry_point.load()
    except Exception as e:
        log.warning(f'Could not load {entry_point.name}.')
        log.debug(str(e))
import pkg_resources

DEFAULT_AUTH = None