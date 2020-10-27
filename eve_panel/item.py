
import param
import panel as pn
from bson import ObjectId
from .eve_model import EveModelBase
from .types import TYPE_MAPPING
from .widgets import get_widget
from .client import EveApiClient, default_client
from .field import EveField

class EveItem(EveModelBase):
    _client = param.ClassSelector(EveApiClient, precedence=-1)
    _resource_url = param.String(precedence=-1)
    _etag = param.String(precedence=-1)
    _version = param.Integer(default=1, bounds=(1,None))

    _save = param.Action(lambda self: self.push, label="Save")
    _delete = param.Action(lambda self: self.delete, label="Delete")
    _clone = param.Action(lambda self: self.clone, label="Clone")

    def __init__(self, **params):
        params["_id"] = params.get("_id", str(ObjectId()))
        if "name" not in params:
            params["name"] = f'{self.__class__.__name__}_{params["_id"]}'
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
            extended_name = f"{name.title()}{field_name.title()}"

            if "allowed" in field_schema:
                class_ = param.Selector
                kwargs["objects"] = field_schema["allowed"]
   
            elif field_schema["type"] in TYPE_MAPPING:
                class_ = EveField(extended_name, field_schema, TYPE_MAPPING[field_schema["type"]])
            else:
                continue
            if "default" in field_schema:
                kwargs["default"] = field_schema["default"]

            widget = get_widget(extended_name, field_schema)
            if widget is not None:
                _widgets[field_name] = widget

            kwargs["allow_None"] = field_schema.get("nullable", False) or not field_schema.get("required", False)
            
            bounds = (field_schema.get("min", None), field_schema.get("max", None))
            if any(bounds):
                kwargs["bounds"] = bounds
            kwargs["readonly"] = field_schema.get("readonly", False)
            params[field_name] = class_(**kwargs)
        params["_widgets"] = param.Dict(default=_widgets, constant=True)
        klass = type(name, (EveItem,), params)
        return klass(_schema=schema,_resource_url=resource_url, _widgets=_widgets, 
                        _client = client or default_client(), **data)
    
    def panel(self):
        header = pn.Column(pn.layout.Divider(), f"### {self.name}",)
        buttons = pn.Param(self.param, parameters=["_save", "_delete"],
                            widgets={"_delete": {"type": pn.widgets.Button, "button_type":"danger"},
                            "_save": {"type": pn.widgets.Button, "button_type":"success"},
                            },
                            show_name=False, default_layout=pn.Row)
        editors = pn.Param(self.param, show_name=False,
                        parameters=list(self._schema or self.param),
                        widgets=self._widgets)
        return pn.Column(header,editors, buttons)
    
    def save(self):
        self.push()

    def to_record(self):
        return {k: getattr(self, k) for k in self._schema}

    def to_dict(self):
        return self.to_record()

    def pull(self, version=1):
        data = self._client.get("/".join(self._resource_url, self._id), version=version)
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
        data = {k: getattr(self, k) for k in self._schema}
        return self.__class__(**data)

    def delete(self):
        url = "/".join(self._resource_url, self._id)
        data = {"_id": self._id, "_etag": self._etag}
        return self._client.delete(url, data)

    def __repr__(self):
        return str(self._id or self.name)