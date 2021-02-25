import param
from bson import objectid
import numpy as np
import pandas as pd
import base64

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

def to_binary(x):
    if isinstance(x, str):
        x = str.encode(x)
    return x

def base64_to_binary(x):
    if isinstance(x, str):
        x = base64.b64decode(x)
    return x

COERCERS = {
    "objectid": str,
    "boolean": bool,
    "binary": to_binary,
    "date": pd.to_datetime,
    "datetime": pd.to_datetime,
    "dict": dict,
    "float": float,
    "integer": int,
    "list": list,
    "number": float,
    "set": set,
    "string": str,
    "media": base64_to_binary,
}

