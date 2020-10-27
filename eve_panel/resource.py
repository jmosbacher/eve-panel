
import param
import panel as pn
import pandas as pd
import json
import yaml
import itertools
from eve.io.mongo.validation import Validator
from io import StringIO, BytesIO

from .eve_model import EveModelBase
from .item import EveItem
from .client import EveApiClient, default_client
from .page import EvePage, EvePageCache, PageZero
from . import settings

def read_csv(f):
    df = pd.read_csv(f).dropna(axis=1, how="all")
    return df.to_dict(orient="records")

file_readers = {
    "json": json.load,
    "yml": yaml.safe_load,
    "yaml": yaml.safe_load,
    "csv": read_csv,
}

def read_file(fname, f):
    name, _, ext = fname.rpartition(".")
    if ext in file_readers:
        data = file_readers[ext](f)
        if isinstance(data, list):
            return data
        elif isinstance(data, (dict,)):
            return [data]
    return []

def items_to_dataframe(items):
    return pd.DataFrame([item.to_dict() for item in items])


class EveResource(EveModelBase):
    _client = param.ClassSelector(EveApiClient, precedence=-1)
    _url = param.String(precedence=-1)
    _page_view_format = param.Selector(objects=["Table", "Widgets", "JSON"], default="Table",
                                         label="Display Format", precedence=1)
    _error_log = param.String("", precedence=1)
    _resource = param.Dict(default={}, constant=True, precedence=-1)
    _schema = param.Dict(default={}, constant=True, precedence=-1)

    _cache = param.ClassSelector(class_=EvePageCache, default=EvePageCache())
    _item_class = param.ClassSelector(EveItem, is_instance=False, precedence=-1)
    _upload_buffer = param.List(default=[], precedence=-1)
    _file_buffer = param.ClassSelector(bytes)
    _filename = param.String()
    selection = param.ListSelector(default=[], objects=[], precedence=-1)
    
    filters = param.Dict(default={}, doc="Filters")
    columns = param.List(default=[], precedence=1)
    # projection = param.Dict(default={}, doc="Projections")

    items_per_page = param.Integer(default=10, label="Items per page", precedence=1)
    _prev_page_button = param.Action(lambda self: self.decrement_page(), label="<<", precedence=1)
    page_number = param.Integer(default=0, bounds=(0, None), label="", doc="Page number", precedence=2)
    _next_page_button = param.Action(lambda self: self.increment_page(), label=">>", precedence=3)
    
    @classmethod
    def from_resource_def(cls, resource_name, resource_def, client=None, items=[]):
        resource = dict(resource_def)
        schema = resource.pop("schema")
        client = client or default_client()
        item = EveItem.from_schema(resource["item_title"], schema, resource["url"] , client=client)
        item_class = item.__class__
        params = dict(
            name = resource["resource_title"],
            _url = resource["url"],
            _client = client,
            _item_class = item_class,
            _resource = resource,
            _schema = schema,
            columns=list(schema)
        )
        return cls(**params)

    def __getitem__(self, key):
        if key in self._cache:
            return self._cache[key]
        data = self._client.get("/".join([self._url, key]))
        if data:
            item = self._item_class(**data)
            return item
        raise KeyError
    
    def __setitem__(self, key, value):
        self._cache[key] = value

    @param.depends("_upload_buffer")
    def upload_view(self):
        clear_button = pn.widgets.Button(name="Clear buffer", 
                                        button_type="warning", 
                                        width=int(settings.GUI_WIDTH/4))
        clear_button.on_click(lambda event: self.clear_buffer())

        upload_file = pn.widgets.FileInput(accept=",".join([f".{ext}" for ext in file_readers]), 
                                            width=int(settings.GUI_WIDTH/4))
        upload_file.link(self, filename="_filename", value="_file_buffer")
        upload_file_button = pn.widgets.Button(name="Read file", button_type="primary", width=int(settings.GUI_WIDTH/4))
        upload_file_button.on_click(lambda event: self._read_file_buffer())

        upload_preview = pn.pane.JSON(self._upload_buffer, name='Upload Buffer',
                                    height=int(settings.GUI_HEIGHT-50),
                                    width=int(settings.GUI_WIDTH), theme="light")
        upload_button = pn.widgets.Button(name="Insert to DB", button_type="success", 
                                            width=int(settings.GUI_WIDTH/4))
        upload_button.on_click(lambda event: self.flush_buffer())
        read_clipboard_button = pn.widgets.Button(name="Read Clipboard", button_type="primary",
                                                     width=int(settings.GUI_WIDTH/4))
        read_clipboard_button.on_click(lambda event: self.read_clipboard())

        first_row_buttons = pn.Row(upload_file, upload_file_button,read_clipboard_button)
        second_row_buttons = pn.Row(clear_button, upload_button)
        input_buttons = pn.Column(first_row_buttons, second_row_buttons)
        error_log = pn.Param(self.param._error_log, width=settings.GUI_WIDTH, height=160,
                        widgets={"_error_log": {"type": pn.widgets.TextAreaInput, "disabled":True, "height":150}})
        upload_view = pn.Column(input_buttons, upload_preview, error_log)
        return upload_view

    @param.depends("page_number", "_cache", "_page_view_format")
    def current_page_view(self):
        page = self.get_page(self.page_number)
        if page is None:
            return pn.panel(f"## No data for page {self.page_number}.")
        return getattr(page, self._page_view_format.lower()+"_view", page.panel)()
       
    def make_panel(self, client=True, tabs_location='above'):
        # if self._panel is not None:
        #     return self._panel
        buttons = pn.Param(self.param, parameters=["_prev_page_button", "page_number", "_next_page_button"],
                             default_layout=pn.Row, name="", width=int(settings.GUI_WIDTH/3))
        # column_select = pn.widgets.MultiChoice(name="Columns", value=list(self._schema),
        #                      options=list(self._schema), width=int(settings.GUI_WIDTH))
        # column_select.link(self, value="columns")
        column_select = pn.Param(self.param.columns, width=int(settings.GUI_WIDTH-30), 
                                 widgets={"columns": {"type": pn.widgets.MultiChoice,
                                                    "options": list(self._schema),
                                                    "width": int(settings.GUI_WIDTH-30)}})

        page_settings = pn.Column(pn.Row(self.param.items_per_page, self.param.filters, self.param._page_view_format,
                                             width=int(settings.GUI_WIDTH-50)),
                                     column_select,
                                      width=int(settings.GUI_WIDTH-10))
        if client:
            page_settings.append("## API client")
            page_settings.append(pn.layout.Divider())
            page_settings.append(self._client.panel)
        
        header = pn.Row(f"## {self.name} resource",
            pn.Spacer(sizing_mode='stretch_both'),
            buttons,
            pn.Spacer(sizing_mode='stretch_both'),
            self._client.busy_indicator,)

        view = pn.Column(
            header,
            pn.Tabs(("Data", self.current_page_view), 
                    ("Settings", page_settings),
                    ("Upload", self.upload_view),
                    dynamic=True, tabs_location=tabs_location,
                    width=int(settings.GUI_WIDTH),
                         )
        )
        
        return view
    
    @property
    def projection(self):
        return { k:1 for k in self.columns }

    def read_clipboard(self):
        from pandas.io.clipboard import clipboard_get
        try:
            self._upload_buffer = json.loads(clipboard_get())
        except Exception as e:
            print(e)

    @param.depends("_file_buffer", watch=True)
    def _read_file_buffer(self):
        sio = BytesIO(self._file_buffer)
        data = read_file(self._filename, sio)
        self._upload_buffer = self._upload_buffer + data
        
    @property
    def gui(self):
        return self.panel()
    
    @property
    def df(self):
        return self.to_dataframe()

    def keys(self):
        for i in itertools.count():
            idx = i+1
            items = self.find(projection={"_id":1}, max_results=5000, page=idx)
            if not items:
                break
            for item in items:
                yield item._id

    def values(self):
        for i in itertools.count():
            idx = i+1
            page = self.get_page(idx)
            if not len(page):
                break
            yield from page.values()

    def items(self):
        for i in itertools.count():
            idx = i+1
            page = self.get_page(idx)
            if not len(page):
                break
            yield from page.items()

    def new_item(self, data={}):
        item = self.item_class(**data)
        self[item._id] = item

    def to_records(self):
        return [item.to_dict() for item in self.values()]
    
    def to_dataframe(self):
        data = list(self.values())
        df = pd.concat([page.to_dataframe() for page in self.values])
        if "_id" in df.columns:
            df = df.set_index("_id")
        return df
    
    def pull(self):
        for i in itertools.count():
            idx = i+1
            if not self.pull_page(idx):
                break
            
    def push(self, idxs=None):
        if idxs is None:
            idxs = list(self._cache.keys())
        for idx in idxs:
            self._cache[idx].push()

    def find(self, query={}, projection={}, max_results=25, page=1):
        resp = self._client.get(self._url, where=json.dumps(query),
                 projection=json.dumps(projection), max_results=max_results, page=page)
        if not resp or "_items" not in resp:
            return []
        items = [self._item_class(**doc) for doc in resp["_items"]]
        return items
    
    def find_df(self, query={}, projection={}, max_results=25, page=1):
        items = [item.to_dict() for item in self.find(query, projection, max_results=max_results, page=page)]
        df = pd.DataFrame(items)
        if "_id" in df.columns:
            df = df.set_index("_id")
        return df

    def post(self, docs):
        return self._cleint.post(self._url, json=docs)

    def add_data(self, data):
        if isinstance(data, dict):
            data = [data]
        docs = []
        for doc in data:
            if isinstance(doc, dict):
                docs.append(doc)
            elif isinstance(doc, EveItem):
                docs.append(doc.to_dict())
        valid = _validate_docs(docs)
        self._upload_buffer = self._upload_buffer + docs

    def _validate_docs(self, docs):
        v = Validator(self._schema)
        valid = []
        rejected = []
        errors = []
        for doc in docs:
            if v.validate(doc):
                valid.append(doc)
            else:
                rejected.append(doc)
                errors.append(v.errors)
        return valid, rejected, errors

    def clear_buffer(self):
        self._upload_buffer = []

    def flush_buffer(self):
        valid, rejected, errors = self._validate_docs(self._upload_buffer)
        if valid:
            self._client.post(self._url, valid)
        self._upload_buffer = rejected
        self._error_log = "/n".join([str(err) for err in errors])

    def pull_page(self, idx=0):
        if not idx:
            self._cache[idx] = PageZero() #EvePage(name=f'{self._url.replace("/", ".")} page 0',_columns=self.columns)
            return False
        items = self.find(query=self.filters, projection=self.projection, 
                            max_results=self.items_per_page, page=idx)
        if items:
            self._cache[idx] = EvePage(name=f'{self._url.replace("/", ".")} page {idx}',
                                    _items={item._id:item for item in items},
                                    _columns=self.columns)
            return True
        return False

    def push_page(self, idx):
        if not idx in self._cache or len(self._cache[idx]):
            return
        self._cache[idx].push()

    def get_page(self, idx):
        if idx not in self._cache or not len(self._cache[idx]):
            self.pull_page(idx)
            # EvePage(_columns=self.columns)
        return self._cache.get(idx, EvePage(name="Place holder", _columns=self.columns))

    def get_page_records(self, idx):
        return self.get_page(idx).to_records()

    def get_page_df(self, idx):
        df = self.get_page(idx).to_dataframe()
        df = df[[col for col in self.columns if col in df.columns]]
        if "_id" in df.columns:
            df = df.set_index("_id")
        return df

    def increment_page(self):
        self.page_number = self.page_number + 1

        
    def next_page(self):
        self.increment_page()
        return self.current_page()

    def current_page(self):
        return self.get_page(self.page_number)

    def decrement_page(self):
        if self.page_number > 1:
            try:
                self.page_number = self.page_number - 1
            except:
                pass
        
    def previous_page(self):
        self.decrement_page()
        return self.current_page()

    @param.depends("items_per_page", "filters", "columns", watch=True)
    def _query_settings_changed(self):
        self._cache = EvePageCache()
        