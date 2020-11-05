import itertools
import json
from io import BytesIO, StringIO

import pandas as pd
import panel as pn
import param
import yaml
import typing
from typing import Union
from . import settings
from .eve_model import EveModelBase
from .field import SUPPORTED_SCHEMA_FIELDS, Validator
from .http_client import DEFAULT_HTTP_CLIENT, EveHttpClient
from .item import EveItem
from .page import EvePage, EvePageCache, PageZero
from .io import FILE_READERS, read_file



class EveResource(EveModelBase):
    """
    Interface for an Eve resource.
    Should be instantiated using an Eve resource definition:
        EveResource.from_resource_def(definition, name)

    Inheritance:
        EveModelBase:

    """
    _http_client = param.ClassSelector(EveHttpClient, precedence=-1)
    _url = param.String(precedence=-1)
    _page_view_format = param.Selector(objects=["Table", "Widgets", "JSON"],
                                       default=settings.DEFAULT_VIEW_FORMAT,
                                       label="Display Format",
                                       precedence=1)
    upload_errors = param.List(default=[])
    _resource = param.Dict(default={}, constant=True, precedence=-1)
    _schema = param.Dict(default={}, constant=True, precedence=-1)

    _cache = param.ClassSelector(class_=EvePageCache, default=EvePageCache())
    _item_class = param.ClassSelector(EveItem,
                                      is_instance=False,
                                      precedence=-1)
    _upload_buffer = param.List(default=[], precedence=-1)
    _file_buffer = param.ClassSelector(bytes)
    _filename = param.String()
    selection = param.ListSelector(default=[], objects=[], precedence=-1)

    filters = param.Dict(default={}, doc="Filters")
    columns = param.List(default=[], precedence=1)

    items_per_page = param.Integer(default=10,
                                   label="Items per page",
                                   precedence=1)
    _prev_page_button = param.Action(lambda self: self.decrement_page(),
                                     label="\u23EA",
                                     precedence=1)
    page_number = param.Integer(default=0,
                                bounds=(0, None),
                                label="",
                                doc="Page number",
                                precedence=2)
    _reload_page_button = param.Action(lambda self: self.reload_page(),
                                     label="\u21BB",
                                     precedence=3)
    _next_page_button = param.Action(lambda self: self.increment_page(),
                                     label="\u23E9",
                                     precedence=4)

    @classmethod
    def from_resource_def(cls,
                          resource_def: dict,
                          resource_name: str,
                          http_client: EveHttpClient = None):
        """Generate a resource interface from a Eve resource definition. 

        Args:
            resource_def (dict): Eve resource definition
            resource_name (str): Name to use for this resource
            http_client (EveHttpClient, optional): http client to use. Defaults to None.
            

        Returns:
            EveResource: Interface to the remote resource.
        """
        
        resource = dict(resource_def)
        schema = resource.pop("schema")
        if http_client is None:
            http_client = DEFAULT_HTTP_CLIENT()
        item = EveItem.from_schema(resource["item_title"].replace(" ", "_"),
                                   schema,
                                   resource["url"],
                                   http_client=http_client)
        item_class = item.__class__
        params = dict(name=resource["resource_title"].replace(" ", "_"),
                      _url=resource["url"],
                      _http_client=http_client,
                      _item_class=item_class,
                      _resource=resource,
                      _schema=schema,
                      columns=list(schema))
        return cls(**params)

    def __getitem__(self, key):
        if key in self._cache:
            return self._cache[key]
        data = self._http_client.get("/".join([self._url, key]))
        if data:
            item = self.make_item(**data)
            return item
        raise KeyError

    def __setitem__(self, key, value):
        self._cache[key] = value

    def make_item(self, **kwargs):
        """Generate EveItem from key value pairs

        Returns:
            EveItem: EveItem instance that enforces schema of current resource.
        """
        return self._item_class(**kwargs, _http_client=self._http_client)

    @property
    def projection(self):
        return {k: 1 for k in self.columns if k not in settings.META_COLUMNS}

    def read_clipboard(self):
        from pandas.io.clipboard import clipboard_get
        try:
            self._upload_buffer = self.filter_docs(json.loads(clipboard_get()))
        except Exception as e:
            print(e)

    def read_file(self, f: typing.BinaryIO=None, ext: str="csv"):
        """Read file into the upload buffer.

        Args:
            f (File, optional): file like object. Defaults to None.
            ext (str, optional): file extension. Defaults to "csv".

        Returns:
            list: documents read
        """
        if f is None:
            f = open(f, "rb")
        data = read_file(f, ext)
        self._upload_buffer = self.filter_docs(data)
        return data

    @param.depends("_file_buffer", watch=True)
    def _read_file_buffer(self):
        sio = BytesIO(self._file_buffer)
        _,_, ext = self._filename.rpartition(".")
        self.read_file(sio, ext)

    def filter_docs(self, docs):
        if isinstance(docs, dict):
            docs = [docs]
        return [{k: v
                 for k, v in doc.items() if k in self._schema} for doc in docs]

    @property
    def gui(self):
        return self.panel()

    @property
    def df(self):
        return self.to_dataframe()

    def keys(self):
        for page in self.pages():
            yield from page.keys()

    def values(self):
        for page in self.pages():
            yield from page.values()

    def items(self):
        for page in self.pages():
            yield from page.items()

    def records(self):
        for page in self.pages():
            yield from page.records()

    def pages(self, start=1, end=None):
        for idx in itertools.count(start):
            if end is not None and idx > end:
                break
            page = self.get_page(idx)
            if not len(page):
                break
            yield page

    def new_item(self, data={}):
        item = self.item_class(**data)
        self[item._id] = item

    def to_records(self):
        return [item.to_dict() for item in self.values()]

    def to_dataframe(self):
        df = pd.concat([page.to_dataframe() for page in self.values()])
        if "_id" in df.columns:
            df = df.set_index("_id")
        return df

    def pull(self, start=1, end=None):
        for idx in itertools.count(start):
            if end is not None and idx > end:
                break
            if not self.pull_page(idx):
                break

    def push(self, idxs=None):
        if idxs is None:
            idxs = list(self._cache.keys())
        for idx in idxs:
            self._cache[idx].push()

    def find(self, query={}, projection={}, max_results=25, page_number=1):
        """Find documents in the remote resource that match a mongodb query.

        Args:
            query (dict, optional): Mongo query. Defaults to {}.
            projection (dict, optional): Mongo projection. Defaults to {}.
            max_results (int, optional): Items per page. Defaults to 25.
            page_number (int, optional): page to return if query returns more than max_results.\
                                         Defaults to 1.

        Returns:
            list: requested page documents that match query
        """
        resp = self._http_client.get(self._url,
                                     where=json.dumps(query),
                                     projection=json.dumps(projection),
                                     max_results=max_results,
                                     page=page_number)
        docs = []
        if resp and "_items" in resp:
            docs = resp["_items"]
        return docs

    def find_page(self,
                  query={},
                  projection={},
                  max_results=25,
                  page_number=1):
        """Same as find() only returns an EvePage instance

        Args:
            query (dict, optional): [description]. Defaults to {}.
            projection (dict, optional): [description]. Defaults to {}.
            max_results (int, optional): [description]. Defaults to 25.
            page_number (int, optional): [description]. Defaults to 1.

        Returns:
            EvePage: requested page from all items that match the query
        """
        docs = self.find(query=query,
                         projection=projection,
                         max_results=max_results,
                         page_number=page_number)
        items = [self.make_item(**doc) for doc in docs]
        page = EvePage(
            name=f'{self._url.replace("/", ".")} page {page_number}',
            _items={item._id: item
                    for item in items},
            _columns=self.columns)
        return page

    def find_df(self, query={}, projection={}, max_results=25, page_number=1):
        """Same as find() only returns a pandas dataframe

        Args:
            query (dict, optional): [description]. Defaults to {}.
            projection (dict, optional): [description]. Defaults to {}.
            max_results (int, optional): [description]. Defaults to 25.
            page_number (int, optional): [description]. Defaults to 1.

        Returns:
            [type]: [description]
        """
        page = self.find_page(query=query,
                              projection=projection,
                              max_results=max_results,
                              page_number=page_number)
        df = page.to_dataframe()
        if "_id" in df.columns:
            df = df.set_index("_id")
        return df

    def find_one(self, query: dict={}, projection: dict={}):
        docs = self.find(query=query, projection=projection, max_results=1)
        if docs:
            return docs[0]

    def find_one_item(self, query={}, projection={}):
        doc = self.find_one(query=query, projection=projection)
        if doc:
            return self.make_item(**doc)

    def validate_documents(self, docs):
        schema = {
            name:
            {k: v
             for k, v in field.items() if k in SUPPORTED_SCHEMA_FIELDS}
            for name, field in self._schema.items()
        }
        v = Validator(schema)
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

    def post(self, docs):
        data = json.dumps(docs)
        return self._http_client.post(self._url, data=data)

    def insert_documents(self, docs: Union[list, tuple, dict], validate=True) -> tuple:
        """Insert documents into the database

        Args:
            docs (list): Documents to insert.
            validate (bool, optional): whether to validate schema of docs locally. Defaults to True.

        Raises:
            TypeError: raised if docs is not the correct type.

        Returns:
            tuple[list, list, list]: Successfuly inserted, rejected, rejection reasons.
        """
        if isinstance(docs, dict):
            docs = [docs]
        elif isinstance(docs, (tuple,list)):
            docs = list(docs)
        else:
            raise TypeError("Documents must be list/tuple or dict")
        if validate:
            docs, rejected, errors = self.validate_documents(docs)
        else:
            rejected, errors = [], []
        if docs and self.post(docs):
            success = docs
        else:
            success = []
        return success, rejected, errors

    def clear_upload_buffer(self):
        self._upload_buffer = []

    def flush_buffer(self):
        success, rejected, errors = self.insert_documents(self._upload_buffer)
        self._upload_buffer = rejected
        self.upload_errors = [str(err) for err in errors]
        return success

    def pull_page(self, idx=0):
        if not idx:
            self._cache[idx] = PageZero()
            return False
        page = self.find_page(query=self.filters,
                              projection=self.projection,
                              max_results=self.items_per_page,
                              page_number=idx)
        if page._items:
            self._cache[idx] = page
            return True
        return False

    def push_page(self, idx):
        if not idx in self._cache or len(self._cache[idx]):
            return
        self._cache[idx].push()

    def get_page(self, idx):
        if idx not in self._cache or not len(self._cache[idx]):
            self.pull_page(idx)
        return self._cache.get(
            idx, EvePage(name="Place holder", _columns=self.columns))

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

    @param.depends("items_per_page",
                   "filters",
                   "columns",
                   watch=True)
    def clear_cache(self):
        self._cache = EvePageCache()

    def reload_page(self, page_number=None):
        if page_number is None:
            page_number = self.page_number
        self.pull_page(page_number)

    def remove_item(self, _id: str) -> bool:
        return self[_id].delete()

    def filter(self, **filters):
        return self.clone(filters=filters)

    def project(self, **projection):
        value_sum = sum(list(projection.values()))
        if value_sum==0:
            columns = [c for c in self._schema if c not in projection]
        elif value_sum==len(projection):
            columns = list(projection)
        else:
            raise ValueError("Mongo projections can either be inclusive or exclusive but not both.")
        return self.clone(columns=columns)


    @param.depends("_upload_buffer")
    def upload_view(self):
        clear_button = pn.widgets.Button(name="Clear buffer",
                                         button_type="warning",
                                         width=int(settings.GUI_WIDTH / 4))
        clear_button.on_click(lambda event: self.clear_upload_buffer())

        upload_file = pn.widgets.FileInput(accept=",".join(
            [f".{ext}" for ext in FILE_READERS]),
                                           width=int(settings.GUI_WIDTH / 4))
        upload_file.link(self, filename="_filename", value="_file_buffer")
        upload_file_button = pn.widgets.Button(name="Read file",
                                               button_type="primary",
                                               width=int(settings.GUI_WIDTH /
                                                         4))
        upload_file_button.on_click(lambda event: self._read_file_buffer())

        upload_preview = pn.pane.JSON(self._upload_buffer,
                                      name='Upload Buffer',
                                      height=int(settings.GUI_HEIGHT / 2),
                                      width=int(settings.GUI_WIDTH),
                                      theme="light")
        upload_button = pn.widgets.Button(name="Insert to DB",
                                          button_type="success",
                                          width=int(settings.GUI_WIDTH / 4))
        upload_button.on_click(lambda event: self.flush_buffer())
        read_clipboard_button = pn.widgets.Button(name="Read Clipboard",
                                                  button_type="primary",
                                                  width=int(
                                                      settings.GUI_WIDTH / 4))
        read_clipboard_button.on_click(lambda event: self.read_clipboard())

        first_row_buttons = pn.Row(upload_file, read_clipboard_button)
        second_row_buttons = pn.Row(clear_button, upload_button)
        input_buttons = pn.Column(first_row_buttons, second_row_buttons)

        upload_view = pn.Column(input_buttons, self.upload_errors,
                                "### Upload buffer", upload_preview)
        return upload_view

    @param.depends("page_number", "_cache", "_page_view_format")
    def current_page_view(self):
        page = self.get_page(self.page_number)
        if page is None:
            return pn.panel(f"## No data for page {self.page_number}.")
        return getattr(page,
                       self._page_view_format.lower() + "_view", page.panel)()

    @param.depends("upload_errors")
    def upload_errors_view(self):
        alerts = [
            pn.pane.Alert(err, alert_type="danger")
            for err in self.upload_errors
        ]
        return pn.Column(*alerts,
                         height=50,
                         width=int(settings.GUI_WIDTH - 30))

    def make_panel(self, show_client=True, tabs_location='above'):
        buttons = pn.Param(self.param,
                           parameters=[
                               "_prev_page_button", "page_number",
                               "_reload_page_button", "_next_page_button"
                           ],
                           default_layout=pn.Row,
                           name="",
                           width=int(settings.GUI_WIDTH / 3))

        column_select = pn.Param(self.param.columns,
                                 width=int(settings.GUI_WIDTH - 30),
                                 widgets={
                                     "columns": {
                                         "type": pn.widgets.MultiChoice,
                                         "options": list(self._schema) +
                                         settings.META_COLUMNS,
                                         "width": int(settings.GUI_WIDTH - 30)
                                     }
                                 })

        page_settings = pn.Column(pn.Row(self.param.items_per_page,
                                         self.param.filters,
                                         self.param._page_view_format,
                                         width=int(settings.GUI_WIDTH - 50)),
                                  column_select,
                                  width=int(settings.GUI_WIDTH - 10))
        if show_client:
            page_settings.append("### HTTP client")
            page_settings.append(pn.layout.Divider())
            page_settings.append(self._http_client.panel)

        header = pn.Row(
            f"## {self.name} resource",
            pn.Spacer(sizing_mode='stretch_both'),
            buttons,
            pn.Spacer(sizing_mode='stretch_both'),
            self._http_client.busy_indicator,
        )

        view = pn.Column(
            header, self._http_client.messages,
            pn.Tabs(
                ("Data", self.current_page_view),
                ("Upload", self.upload_view),
                ("Config", page_settings),
                dynamic=True,
                tabs_location=tabs_location,
                width=int(settings.GUI_WIDTH),
            ))

        return view
