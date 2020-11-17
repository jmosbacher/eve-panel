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


class ConfigParameter(param.Parameter):

    __slots__ = ["env_prefix", "klass", "env_name"]

    def __init__(self, klass, env_prefix="", **kwargs):
        super().__init__(**kwargs)
        self.env_prefix = env_prefix
        self.klass = klass
       
    def _set_names(self, attrib_name):
        env_name = attrib_name.upper()
        self.env_name = self.env_prefix.upper() + "_" + env_name
        super()._set_names(attrib_name)
        
    def __get__(self, obj, objtype):
        if os.getenv(self.env_name, ""):
            env = os.getenv(self.env_name, "")
            try:
                env = json.loads(env)
            except Exception as e:
                pass
            default = self.klass(env)
        else:
            default = self.default
        if obj is None:
            result = default
        else:
            result = obj.__dict__.get(self._internal_name, default)
        return result


class Config(param.Parameterized):
    GUI_MAX_WIDTH = ConfigParameter(int, env_prefix="eve_panel")
    GUI_MAX_HEIGHT = ConfigParameter(int, env_prefix="eve_panel")
    SHOW_INDICATOR = ConfigParameter(bool, env_prefix="eve_panel")
    SIZING_MODE = ConfigParameter(str, env_prefix="eve_panel")

config = Config()