
"""
auth module
====================================
Authentication and Authorization handling
"""

import base64

import panel as pn
import param
import pkg_resources

from .eve_model import EveModelBase


class EveAuthBase(param.Parameterized):
    """Base class for Eve authentication scheme

    Inheritance:
        param.Parameterized:

    """

    def get_headers(self):
        """Generate auth headers for HTTP requests.

        Returns:
            dict: Auth related headers to be included in all requests.
        """
        return {}

    def login(self):
        """perform any actions required to aquire credentials.

        Returns:
            bool: whether login was successful
        """
        return True

    def panel(self):
        """Get the panel representation of this object for GUI

        Returns:
            panel.Viewable: GUI widgets with impotant inputs
                and feedback for the auth scheme
        """
        return pn.Column()

    def set_token(self, token):
        """Set the access token manually.

        Args:
            token ([type]): [description]
        """
        self.token = token


class EveBasicAuth(EveAuthBase):
    """
    Support for eve basic auth.

    Inheritance:
        EveAuthBase:

    """
    
    username = param.String(precedence=1, doc="Basic auth username")
    password = param.String(precedence=2, doc="Basic auth password")
    token = param.ClassSelector(bytes, default=b"", doc="Basic auth token")

    def login(self):
        if not self.token:
            self.token = base64.b64encode(
                f"{self.username}:{self.password}".encode())
        return True

    def get_headers(self):
        self.login()
        return {"Authorization": f"Basic {self.token}"}

    def panel(self):
        return pn.Param(self.param,
                        parameters=["username", "password"],
                        widgets={"password": pn.widgets.PasswordInput})


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

    def login(self):
        return bool(self.token)

    def panel(self):
        return pn.panel(self.param.token)


AUTH_CLASSES = {
    "Basic": EveBasicAuth,
    "Bearer": EveBearerAuth,
}


class AuthSelector(EveAuthBase):
    """
    Allows selecting from available authentication schemes
    """

    auth_options = {k: v()
                    for k, v in AUTH_CLASSES.items()
                    }  #[v() for v in AUTH_CLASSES.values()]

    _auth_object = param.ObjectSelector(
        default=auth_options[list(auth_options)[0]],
        objects=auth_options,
        label="Authentication")
    # _auth = param.ClassSelector(EveAuthBase, default=EveBasicAuth())
    @property
    def token(self):
        return getattr(self._auth_object, "token", "")

    @token.setter
    def token(self, val):
        setattr(self._auth_object, "token", val)

    def login(self):
        return self._auth_object.login()

    def get_headers(self):
        return self._auth_object.get_headers()

    @param.depends("_auth_object")
    def auth_view(self):
        if self._auth_object is None or not hasattr(self._auth_object,
                                                    "panel"):
            return pn.Column()

        return self._auth_object.panel()

    def set_auth_by_name(self, name):
        self._auth_object = self.param._auth_object.names[name]

    def panel(self):
        return pn.Column(self.param._auth_object, self.auth_view)

    def __init__(self, **params):
        super().__init__(**params)
        for entry_point in pkg_resources.iter_entry_points('eve_panel.auth'):
            auth_class = entry_point.load()
            if issubclass(auth_class, EveAuthBase):
                AUTH_CLASSES[entry_point.name] = auth_class
        auth_options = {k: v() for k, v in AUTH_CLASSES.items()}
        self.param._auth_object.objects = list(auth_options.values())
        self.param._auth_object.names = auth_options
        self._auth_object = auth_options[list(auth_options)[0]]
