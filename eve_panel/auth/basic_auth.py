

import base64
import panel as pn
import param
import getpass
import logging
from .base import EveAuthBase


logger = logging.getLogger(__name__)


class EveBasicAuth(EveAuthBase):
    """
    Support for eve basic auth.

    Inheritance:
        EveAuthBase:

    """
    
    username = param.String(precedence=1, doc="Basic auth username")
    password = param.String(precedence=2, doc="Basic auth password")

    @property
    def token(self):
        return base64.b64encode(":".join([self.username, self.password]).encode())

    def login(self, username=None, password=None):
        if username is None:
            username = input("Username: ")
        self.username = username
        if password is None:
            password = getpass.getpass(prompt='Password: ', stream=None) 
        self.password = password
        return True
    
    @property
    def logged_in(self):
        return self.username and self.password

    def logout(self):
        self.username = ""
        self.password = ""
        
    def get_headers(self):
        return {"Authorization": f"Basic {self.token}"}

    def make_panel(self):
        return pn.Param(self.param,
                        max_width=self.max_width,
                        max_height=self.max_height,
                        sizing_mode=self.sizing_mode,
                        parameters=["username", "password"],
                        widgets={"password": pn.widgets.PasswordInput})

    def credentials_view(self):
        return pn.Param(self.param,
                        parameters=["username", "password"],
                        widgets={"password": pn.widgets.PasswordInput},
                        max_width=self.max_width,
                        max_height=self.max_height,
                        sizing_mode=self.sizing_mode,
                        default_layout=pn.Row)
