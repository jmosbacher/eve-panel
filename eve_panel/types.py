import param
from bson import objectid
import numpy as np


class CoerceClassSelector(param.ClassSelector):
    def __set__(self, obj, val):
        try:
            val = self.class_(val)
        except:
            pass
        super().__set__(obj, val)


def objectid_param(**kwargs):
    return CoerceClassSelector(str, constant=True, **kwargs)


def bytes_param(**kwargs):
    return param.ClassSelector(bytes, **kwargs)


def set_param(**kwargs):
    return param.ClassSelector(set, **kwargs)


TYPE_MAPPING = {
    "objectid": objectid_param,
    "boolean": param.Boolean,
    "binary": bytes_param,
    "date": param.Date,
    "datetime": param.Date,
    "dict": param.Dict,
    "float": param.Number,
    "integer": param.Integer,
    "list": param.List,
    "number": param.Number,
    "set": set_param,
    "string": param.String,
    "media": bytes_param,
}

DASK_TYPE_MAPPING = {
    "objectid": str,
    "boolean": bool,
    "binary": bytes,
    "date": np.datetime64,
    "datetime": np.datetime64,
    "dict": dict,
    "float": float,
    "integer": int,
    "list": list,
    "number": float,
    "set": set,
    "string": str,
    "media": bytes,

}

COERCERS = {
    "objectid": str,
    "boolean": bool,
    "binary": bytes,
    "date": np.datetime64,
    "datetime": np.datetime64,
    "dict": dict,
    "float": float,
    "integer": int,
    "list": list,
    "number": float,
    "set": set,
    "string": str,
    "media": bytes,
}