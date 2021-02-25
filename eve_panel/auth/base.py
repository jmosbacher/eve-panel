import logging
import param
import panel as pn

from ..eve_model import EveModelBase
from ..settings import config as settings


logger = logging.getLogger(__name__)


class EveAuthBase(EveModelBase):
    """Base class for Eve authentication scheme

    Inheritance:
        param.Parameterized:

    """

    post_login_hooks = param.HookList([])

    def get_headers(self):
        """Generate auth headers for HTTP requests.

        Returns:
            dict: Auth related headers to be included in all requests.
        """
        raise NotImplementedError

    def login(self):
        """perform any actions required to aquire credentials.

        Returns:
            bool: whether login was successful
        """
        raise NotImplementedError

    def logout(self):
        """perform any actions required to logout.

        Returns:
            bool: whether login was successful
        """
        raise NotImplementedError

    @property
    def logged_in(self):
        raise NotImplementedError

    def set_credentials(self, **credentials):
        """Set the access credentials manually.
        """
        for k,v in credentials.items():
            setattr(self, k, v)
    
    def credentials_view(self):
        raise NotImplementedError

    def post_login(self):
        for hook in self.post_login_hooks:
            hook(self)

class EveNoAuth(EveAuthBase):
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

    def logout(self):
        """perform any actions required to logout.

        Returns:
            bool: whether login was successful
        """
        return True

    def credentials_view(self):
        return pn.Row()

    @property
    def logged_in(self):
        return True
