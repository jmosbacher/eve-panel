GUI_WIDTH = 1000
GUI_HEIGHT = 400
WIDGET_VIEW_ITEMS = 8
DEFAULT_VIEW_FORMAT = "Table"
MAX_LOG_SIZE = 20
MAX_MESSAGES = 3
META_FIELDS = ["_version", "_latest_version", "_etag", "_created"]
SHOW_INDICATOR = True
SIZING_MODE = "stretch_width"
DEBUG = False

import param
import json
import os


class ConfigParameter(param.Parameter):

    __slots__ = ["env_prefix", "klass"]

    def __init__(self, klass, env_prefix="", **kwargs):
        super().__init__(**kwargs)
        self.env_prefix = env_prefix
        self.klass = klass
       
    def _set_names(self, attrib_name):
        env_name = attrib_name.upper()
        env_name = self.env_prefix.upper() + "_" + env_name
        if os.getenv(env_name, ""):
            env = os.getenv(env_name, "")
            try:
                env = json.loads(env)
            except Exception as e:
                pass
            self.default = self.klass(env)
        super()._set_names(attrib_name)
        

class Config(param.Parameterized):
    GUI_MAX_WIDTH = ConfigParameter(int, env_prefix="eve_panel")
    GUI_MAX_HEIGHT = ConfigParameter(int, env_prefix="eve_panel")
    SHOW_INDICATOR = ConfigParameter(bool, env_prefix="eve_panel", default=True)
    SIZING_MODE = ConfigParameter(str, env_prefix="eve_panel", default="stretch_width")
    DEBUG = ConfigParameter(bool, env_prefix="eve_panel", default=False)
    GUI_WIDTH = 1000
    GUI_HEIGHT = 400
    WIDGET_VIEW_ITEMS = 8
    DEFAULT_VIEW_FORMAT = "Table"
    MAX_LOG_SIZE = 20
    MAX_MESSAGES = 3
    META_FIELDS = ["_version", "_latest_version", "_etag", "_created"]
    SHOW_INDICATOR = True
    DEFAULT_TIMEOUT = 20
    IGNORE_ERRORS = False
    
    OAUTH_DOMAIN = ConfigParameter(str, env_prefix="eve_panel", default="http://localhost/oauth")
    OAUTH_CERT_PATH = ConfigParameter(str, env_prefix="eve_panel", default="/.well-know/certs")
    OAUTH_CODE_PATH = ConfigParameter(str, env_prefix="eve_panel", default="/device/code")
    OAUTH_TOKEN_PATH = ConfigParameter(str, env_prefix="eve_panel", default="/token")
    DEFAULT_CLIENT_ID = ConfigParameter(str, env_prefix="eve_panel", default="eve-panel")
    DEFAULT_AUDIENCE = ConfigParameter(str, env_prefix="eve_panel", default="")
    

config = Config()