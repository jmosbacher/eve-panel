
import param
import panel as pn
from bson import ObjectId
from .eve_model import EveModelBase
from .types import TYPE_MAPPING
from .widgets import WIDGET_MAPPING
from .client import EveApiClient, default_client


class EveItem(EveModelBase):
    _client = param.ClassSelector(EveApiClient, precedence=-1)
    _resource_url = param.String(precedence=-1)
    _etag = param.String(precedence=-1)

    _save = param.Action(lambda self: self.push, label="Save")
    _clone = param.Action(lambda self: self.clone, label="Clone")

    def __init__(self, **params):
        params["_id"] = params.get("_id", str(ObjectId()))
        params = {k:v for k,v in params.items() if hasattr(self, k)}
        super().__init__(**params)
  
    @classmethod
    def from_schema(cls, name, schema, resource_url, client=None, data={}):
        params = dict(
            _schema = param.Dict(default=schema, allow_None=False, constant=True),
        )
        _widgets = {}
        for field_name, field_schema in schema.items():
            kwargs = {}
            if "allowed" in field_schema:
                class_ = param.Selector
                kwargs["objects"] = field_schema["allowed"]
            # elif field_schema["type"]=="dict" and "schema" in field_schema:
            #     class_ = EveItem.from_schema(name+"_"+field_name, field_schema["schema"])
    #         elif field_schema["type"]=="list" and "schema" in field_schema:
    #             class_ = param.List
    #             if field_schema["schema"]["type"]=="dict":
    #                 kwargs["class_"] = gen_item_class(name+"_"+field_name, field_schema["schema"]["schema"])       
            elif field_schema["type"] in TYPE_MAPPING:
                class_ = TYPE_MAPPING[field_schema["type"]]
            else:
                continue
            if "default" in field_schema:
                kwargs["default"] = field_schema["default"]
            if field_schema["type"] in WIDGET_MAPPING:
                _widgets[field_name] = WIDGET_MAPPING[field_schema["type"]]
            kwargs["allow_None"] = not field_schema.get("required", False)
            params[field_name] = class_(**kwargs)
        params["_widgets"] = param.Dict(default=_widgets, constant=True)
        klass = type(name, (EveItem,), params)
        return klass(_schema=schema,_resource_url=resource_url, _widgets=_widgets, 
                        _client = client or default_client(), **data)
    
    def panel(self):
        buttons = pn.Param(self.param, parameters=["_save"],
                            show_name=False, default_layout=pn.Row)
        editors = pn.Param(self.param, show_name=False,
                        parameters=list(self._schema or self.param),
                        widgets=self._widgets)
        return pn.Column(editors, buttons)
    
    @property
    def gui(self):
        return self.panel()
    
    def save(self):
        raise NotImplementedError
    
    def to_dict(self):
        return {k: getattr(self, k) for k in self._schema}

    def pull(self):
        data = self._client.get("/".join(self._resource_url, self._id))
        if data:
            for k,v in data.items():
                if hasattr(self, k):
                    setattr(self, k, v) 

    def push(self):
        url = "/".join(self._resource_url, self._id)
        data = {"_id": self._id, "_etag": self._etag}
        for k in self._schema:
            data[k] = getattr(self, k)
        self._client.put(url, data)

    def patch(self, fields):
        url = "/".join(self._resource_url, self._id)
        data = {"_id": self._id, "_etag": self._etag}
        for k in fields:
            data[k] = getattr(self, k)
        self._client.patch(url, data)
    
    def clone(self):
        pass
    
    def __repr__(self):
        return str(self._id or self.name)