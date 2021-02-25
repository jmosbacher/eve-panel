


import base64
import panel as pn
import param
import getpass
import logging

from .base import EveAuthBase

logger = logging.getLogger(__name__)


class EveBearerAuth(EveAuthBase):
    """
    Support for Eve bearer auth.

    Inheritance:
        EveAuthBase:

    """
    token = param.String(doc="Beaer token")

    def get_headers(self):
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        else:
            return {}

    def login(self, token=None):
        if token is None:
            token = input("Access token: ")
        self.token = token
        return bool(self.token)

    def logout(self):
        self.token = ""
        
    @property
    def logged_in(self):
        return bool(self.token)

    def make_panel(self):
        return pn.panel(self.param.token,
                        max_width=self.max_width,
                        max_height=self.max_height,
                        sizing_mode=self.sizing_mode,
        )

    def credentials_view(self):
        return self.panel()