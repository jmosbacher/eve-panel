import numpy as np
import json
from functools import wraps
import re
url_regex = re.compile(
        r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

def is_valid_url(url):
    return re.match(url_regex, url) is not None

def requires_login(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.session.logged_in:
            raise RuntimeError("You are not logged in.")
        return method(self, *args, **kwargs)
    return wrapper

def to_json_compliant(obj):
    if isinstance(obj, np.integer):
            return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj
class NumpyJSONENncoder(json.JSONEncoder):
    def default(self, obj):
        obj = to_json_compliant(obj)
        return super(NumpyJSONENncoder, self).default(obj)

def to_data_dict(doc):
    data = {}
    for k,v in doc.items():
        if isinstance(v, str):
            data[k] = v
        else:
            data[k] = json.dumps(v, cls=NumpyJSONENncoder)
    return data