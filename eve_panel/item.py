import panel as pn
import param
from bson import ObjectId
import json
from io import BytesIO
import logging

from .settings import config as settings
from .eve_model import DefaultLayout, EveModelBase
from .field import EveField
from .session import EveSessionBase
from .types import TYPE_MAPPING
from .widgets import get_widget
from .utils import NumpyJSONENncoder, to_data_dict, to_json_compliant

logger = logging.getLogger(__name__)

class EveItem(EveModelBase):
    session = param.ClassSelector(EveSessionBase, constant=True, precedence=-1)
    _resource_url = param.String(precedence=-1)
    _etag = param.String(allow_None=True, precedence=15)
    _version = param.Integer(default=1,
                             bounds=(1, None),
                             allow_None=True,
                             precedence=13)
    _latest_version = param.Integer(default=1,
                                    bounds=(1, None),
                                    allow_None=True,
                                    constant=True,
                                    precedence=14)

    _save = param.Action(lambda self: self.save(), label="Save", precedence=16)
    _delete = param.Action(lambda self: self.delete(),
                           label="Delete",
                           precedence=16)
    _delete_requested = param.Boolean(False, precedence=-1)
    _deleted = param.Boolean(False, precedence=-1)
    _verification = param.String("Enter item id here to enable deletion.", label="", precedence=1)
    _clone = param.Action(lambda self: self.clone(),
                          label="Clone",
                          precedence=16)
    _reload = param.Action(lambda self: self.pull(),
                          label="Reload",
                          precedence=16)

    def __init__(self, **params):
        params["_id"] = params.get("_id", str(ObjectId()))
        if "name" not in params:
            params["name"] = f'{self.__class__.__name__}_{params["_id"]}'
        params = {k: v for k, v in params.items() if hasattr(self, k)}
        super().__init__(**params)

    @classmethod
    def from_schema(cls,
                    name,
                    schema,
                    resource_url,
                    session=None,
                    data={}):
        
        params = dict(
            schema=param.Dict(default=schema,
                               allow_None=False,
                               constant=True,
                               precedence=-1),
            _resource_url=param.String(default=resource_url, precedence=-1),
        )
        _widgets = {
            "_etag": {
                "type": pn.widgets.TextInput,
                "disabled": True
            },
            "_version": {
                "type": pn.widgets.IntInput,
                "disabled": False
            }
        }

        for field_name, field_schema in schema.items():
            kwargs = {"precedence": 10}
            if field_name == "_id":
                kwargs["precedence"] = 1
            extended_name = f"{name.title()}{field_name.title()}"

            if "allowed" in field_schema:
                class_ = param.Selector
                kwargs["objects"] = field_schema["allowed"]

            elif field_schema["type"] in TYPE_MAPPING:
                class_ = EveField(extended_name, field_schema,
                                  TYPE_MAPPING[field_schema["type"]])
            else:
                continue
            if "default" in field_schema:
                kwargs["default"] = field_schema["default"]
            else:
                kwargs["default"] = None

            widget = get_widget(extended_name, field_schema)
            if widget is not None:
                _widgets[field_name] = widget

            if field_schema.get("required", False):
                kwargs["allow_None"] = False

            bounds = (field_schema.get("min",
                                       None), field_schema.get("max", None))
            if any(bounds):
                kwargs["bounds"] = bounds
            kwargs["readonly"] = field_schema.get("readonly", False)
            params[field_name] = class_(**kwargs)
        params["_widgets"] = param.Dict(default=_widgets,
                                        constant=True,
                                        precedence=-1)
        klass = type(name, (EveItem, ), params)

        return klass(schema=schema,
                     _widgets=_widgets,
                     _resource_url=resource_url,
                     session=session,
                     **data)

    @property
    def url(self):
        return "/".join([self._resource_url, self._id])

    def save(self):
        self.push()

    def to_record(self, exclude_files=True):
        obj = {}
        for k in self.schema:
            v = getattr(self, k)
            if exclude_files and isinstance(v, bytes):
                continue
            obj[k] = v
        return obj

    def to_json(self):
        obj = self.to_record()
        return json.dumps(obj, cls=NumpyJSONENncoder)

    def to_dict(self):
        return self.to_record()

    def keys(self):
        yield from self.to_record().keys()

    def values(self):
        yield from self.to_record().values()

    def items(self):
        yield from self.to_record().items()

    def __getitem__(self, key):
        if key in self.schema:
            return getattr(self, key)
        else:
            raise KeyError(f"{key} not found.")
    
    def __setitem__(self, key, value):
        if key in self.schema:
            setattr(self, key, value)
        else:
            raise KeyError(f"{key} cannot be set.")

    @param.depends("_version", watch=True)
    def pull(self):
        if self._version is None:
            version = 1
        else:
            version = self._version
        with self.session.Client() as client:
            resp = client.get(self.url, params=dict(version=version))
        data = resp.json()
        if not data:
            return
        for k, v in data.items():
            if hasattr(self, k):
                try:
                    param = getattr(self.param, k)
                    if param.constant or param.readonly:
                        setattr(self, getattr(param, "_internal_name"), v)
                    else:
                        self.param.set_param(**{k:v})
                except Exception as e:
                    logger.error(str(e))
                    pass
    
    def get_version(self, version):
        vers = self.clone(_version=version)
        vers.pull()
        return vers
        
    def all_versions(self):
        with self.session.Client() as client:
            resp = client.get(self.url, params=dict(version='all'))
            resp.raise_for_status()
        data = resp.json()
        if not data:
            return []
        return [
            self.__class__(**doc,
                           session=self.session,
                           _resource_url=self._resource_url)
            for doc in data.get("_items", [])
        ]

    def version_diffs(self):
        with self.session.Client() as client:
            resp = client.get(self.url, params=dict(version='diffs'))

        data = resp.json()
        if not data:
            return []
        return [
            self.__class__(**doc,
                           session=self.session,
                           _resource_url=self._resource_url)
            for doc in data.get("_items", [])
        ]

    def push(self):
        headers = {"Content-Type": "application/json"}
        if self._version == self._latest_version:
            headers["If-Match"] = self._etag
        data = {k: getattr(self, k) for k in self.schema if not k.startswith("_")}
        doc = {k:v for k,v in data.items() if v is not None}
        files = {name: BytesIO(doc.pop(name)) for name, value in data.items()
                    if isinstance(value, bytes)}
        # data = to_data_dict(doc)
        data = json.dumps(data, cls=NumpyJSONENncoder)
        with self.session.Client(headers=headers) as client:
            resp = client.put(self.url, data=data, files=files, )
        self.pull()

    def patch(self, *fields):
        headers = {"Content-Type": "application/json"}
        if self._version == self._latest_version:
            headers["If-Match"] = self._etag
            
        data = {}
        for k in fields:
            data[k] = getattr(self, k)
        doc = {k:v for k,v in data.items() if v is not None}
        files = {name: BytesIO(doc.pop(name)) for name, value in data.items() if isinstance(value, bytes)}
        # data = to_data_dict(doc)
        data = json.dumps(data, cls=NumpyJSONENncoder)

        with self.session.Client() as client:
            resp = client.patch(self.url, data=data, files=files, headers=headers)
            resp.raise_for_status()
        self.pull()

    def delete(self, verification=None):
        if verification is not None and verification != self._id:
            print(verification)
            return False
        headers ={}
        if self._version == self._latest_version:
            headers["If-Match"] = self._etag
        with self.session.Client() as client:
            resp = client.delete(self.url, headers=headers)
            self._deleted = True
        return self._deleted

    # def clone(self, **kwargs):
    #     data = {k: getattr(self, k) for k in self.schema}
    #     data.update(kwargs)
    #     return self.__class__(**data)

    @param.depends("_delete_requested")
    def buttons(self):
        param_buttons = pn.Param(self.param,
                           parameters=["_reload", "_save"],
                           widgets={
                               "_reload": {
                                   "type": pn.widgets.Button,
                                   "button_type": "primary"
                               },
                               "_save": {
                                   "type": pn.widgets.Button,
                                   "button_type": "success"
                               },
                           },
                           show_name=False,
                           default_layout=pn.Row)

        delete_button = pn.widgets.Button(name="Remove", align="center", max_width=50)
        verification = pn.widgets.TextInput(placeholder="Enter item id here to enable deletion.")
        row = pn.Row(param_buttons, verification, delete_button)
        if self._deleted:
            delete_button.name = "Deleted."
            delete_button.disabled = True
            row.pop(1)
        elif self._delete_requested:
            delete_button.name = "Delete"
            delete_button.button_type = "danger"
            def onclick(event):
                delete_button.disabled = True
                self.delete(verification=verification.value)
                delete_button.disabled = False
            delete_button.on_click(onclick)
        else:
            delete_button.disabled = False
            delete_button.button_type = "warning"
            def onclick(event):
                self._delete_requested = True
            delete_button.on_click(onclick)
            row.pop(1)
        return row

    def make_panel(self):
        header = pn.Column(
            pn.layout.Divider(),
            f"### {self.name}",
            width_policy='max',
            sizing_mode=self.sizing_mode,
            width=self.max_width,
        )
        
        # buttons = pn.Row(param_buttons, self.delete_button)
    
        editors = pn.Param(self.param,
                           show_name=False,
                           default_layout=DefaultLayout,
                           widgets=self._widgets,
                           parameters=list(self.schema)+settings.META_FIELDS,
                           width_policy='max',
                           sizing_mode=self.sizing_mode,
                           width=self.max_width,
                           )
        # media_previews = 
        return pn.Column(header,
                        editors,
                        self.buttons,
                        width_policy='max',
                        sizing_mode=self.sizing_mode,
                        width=self.max_width,
                        )

    def __repr__(self):
        return f"{self.__class__.__name__}(_id={self._id or self.name})"
