import itertools
import json
from io import BytesIO, StringIO
import time
import pandas as pd
import panel as pn
import param
import yaml
import typing
import math
from typing import Union, List, Dict, Tuple
import multiprocessing as mp

from . import settings
from .eve_model import EveModelBase
from .field import SUPPORTED_SCHEMA_FIELDS, Validator
from .http_client import DEFAULT_HTTP_CLIENT, EveHttpClient
from .item import EveItem
from .page import EvePage, EvePageCache, PageZero
from .io import FILE_READERS, read_data_file
from .types import DASK_TYPE_MAPPING, COERCERS

try:
    from ruamel.yaml import YAML
    yaml = YAML()
    yaml.indent(mapping=4, sequence=4, offset=2)
except ImportError:
    import yaml

class EveResource(EveModelBase):
    """
    Interface for an Eve resource.
    Should be instantiated using an Eve resource definition:
        EveResource.from_resource_def(definition, name)

    Inheritance:
        EveModelBase:

    """
    _paste_bin = param.ClassSelector(class_=pn.widgets.Ace, default=None, )
    _http_client = param.ClassSelector(EveHttpClient, precedence=-1)
    _url = param.String(precedence=-1)
    _page_view_format = param.Selector(objects=["Table", "Widgets", "JSON"],
                                       default=settings.DEFAULT_VIEW_FORMAT,
                                       label="Display Format",
                                       precedence=1)
    upload_errors = param.List(default=[])
    _resource_def = param.Dict(default={}, constant=True, precedence=-1)
    schema = param.Dict(default={}, constant=True, precedence=-1)

    _cache = param.ClassSelector(class_=EvePageCache, default=EvePageCache())
    _item_class = param.ClassSelector(EveItem,
                                      is_instance=False,
                                      precedence=-1)
    # _upload_buffer = param.List(default=[], precedence=-1)
    _upload_buffer = param.String(default="", precedence=1)
    _file_buffer = param.ClassSelector(bytes)
    _filename = param.String()

    filters = param.Dict(default={}, doc="Filters")
    fields = param.List(default=[], precedence=1)
    sorting = param.List(default=[], precedence=1)

    items_per_page = param.Integer(default=100,
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
                                     precedence=4)
    _next_page_button = param.Action(lambda self: self.increment_page(),
                                     label="\u23E9",
                                     precedence=3)
    _clear_cache_button = param.Action(lambda self: self.clear_cache(),
                                     label="\u2672",
                                     precedence=5)
    _plot_selection = param.String("None")
    _plot = param.Parameter(default=None)

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
        plots = list(resource.get("metadata", {}).get("plots", {}))
        params = dict(name=resource["resource_title"].replace(" ", "_"),
                      _url=resource["url"],
                      _http_client=http_client,
                      _item_class=item_class,
                      _resource_def=resource,
                      schema=schema,
                      fields=list(schema))
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
        return {k: 1 for k in self.fields if k not in settings.META_FIELDS}
    
    @property
    def paste_bin(self):
        if self._paste_bin is None:
            self._paste_bin = pn.widgets.Ace(name="Paste Bin", value=json.dumps(self.schema, indent=4),
                                             language="json", width=int(self.max_width-50))
        return self._paste_bin
    
    @property
    def field_options(self):
        return list(self.schema) + settings.META_FIELDS

    @property
    def nitems(self):
        resp = self.get(where=self.filters,
                        projection={"_id": 1},
                        max_results=1,
                        page=1,
                        )
        if "_meta" in resp:
            return int(resp["_meta"].get("total", 0))
        else:
            raise ConnectionError("Unable to connect to server.")
    
    @property
    def is_table(self):
        return not any([v["type"] in ['list', 'dict'] for v in self.schema.values()])

    @property
    def page_options(self):
        return list(range(1, math.ceil(self.nitems/self.items_per_page)+1))

    @property
    def sorting_options(self)->list:
        """Returns valid options for the sorting attribute.

        Returns:
            list: list of fields
        """
        return self.field_options + [f"-{col}" for col in self.field_options]

    @property
    def metadata(self) -> dict:
        """Resource metadata

        Returns:
            dict: Resource metadata
        """
        return self._resource_def.get("metadata", {})

    def read_clipboard(self):
        """Read clipboard into uplaod buffer.
        """
        from pandas.io.clipboard import clipboard_get
        try:
            self.paste_bin.value = clipboard_get()
        except Exception as e:
            print(e)

    def read_file(self, f: typing.Union[typing.BinaryIO, str]=None, ext: str="csv"):
        """Read file into the upload buffer.

        Args:
            f (File, optional): file like object. Defaults to None.
            ext (str, optional): file extension. Defaults to "csv".

        Returns:
            list: documents read
        """
        if isinstance(f, str):
            f = open(f, "rb")
        data = read_data_file(f, ext)
        self.paste_bin.value = json.dumps(data, indent=4)
        return data

    @param.depends("_file_buffer", watch=True)
    def _read_file_buffer(self):
        sio = BytesIO(self._file_buffer)
        _,_, ext = self._filename.rpartition(".")
        self.read_file(sio, ext)

    def filter_fields(self, docs: Union[Dict, List[Dict]]) -> List[Dict]:
        """Filter only fields that are in the resource schema for a list of documents.

        Args:
            docs (Union[dict, list[dict]]): list of documents or single document.

        Returns:
            list[dict]: list of filtered documents.
        """
        if isinstance(docs, dict):
            docs = [docs]
        return [{k: v
                 for k, v in doc.items() if k in self.schema} for doc in docs]

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
        df = pd.concat([page.to_dataframe() for page in self.pages()])
        if "_id" in df.columns:
            df = df.set_index("_id")
        return df
    
    def to_dask(self, pages=None, persist=False, clone=True):
        try:
            import dask
        except ImportError:
            raise RuntimeError("Dask is not installed.")
        if clone:
            resource = self.clone()
        else:
            resource = self
        if pages is None:
            pages = resource.page_options
        columns = [(k, DASK_TYPE_MAPPING[v["type"]]) for k,v in resource.schema.items() 
                                    if k in self.fields and not k.startswith("_")]
        column_types = dict(columns)

        url = self._url
        client_kwargs = self._http_client.get_client_kwargs()

        def get_data(params):
            import httpx
            if client_kwargs["app"] is not None:
                from eve import Eve
                client_kwargs["app"] = Eve(settings=client_kwargs["app"])
            items = []
            with httpx.Client(**client_kwargs) as client:
                try:
                    resp = client.get(url, params=params, timeout=15)
                    items = resp.json().get("_items", [])
                except:
                    pass
            data = [{k:column_types[k](v) for k,v in item.items() if k in column_types} for item in items]
            return data
        
        if not self.is_table:
            import dask.bag as db
            return db.from_sequence([self.get_page_kwargs(i) for i in pages]).map(get_data).flatten()

        import dask.dataframe as dd
        import pandas as pd
        
        def get_df(params):
            data = get_data(params)
            return pd.DataFrame(data, columns=list(column_types))
        dask_name = str(hash((resource.name, )+tuple(self.get_page_kwargs(1).values())))
        dsk = {(dask_name, i-1): (get_df, self.get_page_kwargs(i)) for i in pages}
        nitems = resource.nitems
        
        divisions = list(range(0, nitems, resource.items_per_page))
        if nitems not in divisions:
           divisions = divisions + [resource.nitems]
        df = dd.DataFrame(dsk, dask_name, columns, divisions)
        if persist:
            return df.persist()
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

    def get(self, **kwargs):
        kwargs = {k:v if isinstance(v, str) else json.dumps(v) for k,v in kwargs.items()}
        default_timeout = 5+int(kwargs.get("max_results", 100))*0.05
        kwargs["timeout"] = kwargs.get("timeout", default_timeout)
        return self._http_client.get(self._url, **kwargs)

    def find(self, query={}, projection={}, sort="", max_results=25, page_number=1):
        """Find documents in the remote resource that match a mongodb query.

        Args:
            query (dict, optional): Mongo query. Defaults to {}.
            projection (dict, optional): Mongo projection. Defaults to {}.
            sort (Union[string, list[tuple]], optional): Sorting either string as e.g:
                                 city,-lastname or list as e.g: [("city", 1), ("lastname", -1)]
            max_results (int, optional): Items per page. Defaults to 25.
            page_number (int, optional): page to return if query returns more than max_results.\
                                         Defaults to 1.

        Returns:
            list: requested page documents that match query
        """

        resp = self.get(where=query,
                        projection=projection,
                        sort=sort,
                        max_results=max_results,
                        page=page_number)
        docs = []
        if resp and "_items" in resp:
            docs = resp["_items"]
        return docs

    def find_page(self, **kwargs):
        """Same as :meth:`eve_panel.EveResource.find()`, only returns an EvePage instance
        """
        docs = self.find(**kwargs)
        items = [self.make_item(**doc) for doc in docs]
        page_number = kwargs.get("page_number", self.page_number)
        page = EvePage(
            name=f'{self._url.replace("/", ".")} page {page_number}',
            _items={item._id: item
                    for item in items},
            fields=self.fields)
        return page

    def find_df(self, **kwargs):
        """Same as :meth:`eve_panel.EveResource.find()`, only returns a pandas dataframe

        """
        page = self.find_page(**kwargs)
        df = page.to_dataframe()
        if "_id" in df.columns:
            df = df.set_index("_id")
        return df

    def find_one(self, query: dict={}, projection: dict={}) -> dict:
        """Find the first document that matches the query,
                 optionally project only given fields.

        Args:
            query (dict, optional): Mongo qury to perform. Defaults to {}.
            projection (dict, optional): Mopngo projection. Defaults to {}.

        Returns:
            Union[dict, None]: If document found, returns it. If not returns None.
        """
        docs = self.find(query=query, projection=projection, max_results=1)
        if docs:
            return docs[0]

    def find_one_item(self, **kwargs):
        doc = self.find_one(**kwargs)
        if doc:
            return self.make_item(**doc)

    def validate_documents(self, docs: List[Dict], coerce=True) -> Tuple:
        """Validates documents against resource schema

        Args:
            docs (list[dict]): list of documents to insert

        Returns:
            tuple[list,list,list]: tuple of documents lists: (valid, rejected, errors) 
        """
        schema = {
            name:
            {k: v
             for k, v in field.items() if k in SUPPORTED_SCHEMA_FIELDS}
            for name, field in self.schema.items()
        }
        if coerce:
            for sch in schema.values():
                if sch["type"] in COERCERS:
                    sch["coerce"] = COERCERS[sch["type"]]
        v = Validator(schema)
        valid = []
        rejected = []
        errors = []
        for doc in docs:
            if v.validate(doc):
                valid.append(v.document)
            else:
                rejected.append(doc)
                errors.append(v.errors)
        return valid, rejected, errors

    def post(self, docs):
        data = json.dumps(docs)
        return self._http_client.post(self._url, data=data, timeout=int(5+len(docs)*0.1))

    def insert_documents(self, docs: Union[list, tuple, dict], validate=True, dry=False) -> tuple:
        """Insert documents into the database

        Args:
            docs (list): Documents to insert.
            validate (bool, optional): whether to validate schema of docs locally. Defaults to True.
            dry (bool, optional): Enable dry run, will validate but not insert documents into DB. Defaults to False.

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
        if dry:
            success = docs
        elif docs and self.post(docs):
            success = docs
        else:
            success = []
        return success, rejected, errors

    def clear_upload_buffer(self):
        """Discards the current upload buffer.
        """
        self.paste_bin.value = ""

    def flush_buffer(self, dry=False):
        """Attempts to insert docs in current upload buffer.

        Args:
            dry (bool, optional): Only validate docs with actually inserting them to DB.
                                Defaults to False.

        Returns:
            list: List of succesfully inserted documents.
        """
        try:
            docs = json.loads(self.paste_bin.value)
        except:
            self.upload_errors = ["Cannot read data. is it valid json?"]
            return []

        if isinstance(docs, dict):
            docs = [docs]
        success, rejected, errors = self.insert_documents(docs, dry=dry)
        if not dry:
            self.paste_bin.value = json.dumps(rejected)
        self.upload_errors = [str(err) for err in errors]
        return success

    def pull_page(self, idx=0, cache_result=True):
        if not idx and cache_result:
            self._cache[idx] = PageZero()
            return False
        page = self.find_page(query=self.filters,
                              projection=self.projection,
                              sort=",".join(self.sorting),
                              max_results=self.items_per_page,
                              page_number=idx)
        if page._items and cache_result:
            self._cache[idx] = page
        return page

    def get_page_kwargs(self, idx):
        kwargs =  dict(
            where=self.filters,
            projection=self.projection,
            sort=",".join(self.sorting),
            max_results=self.items_per_page,
            page=idx
        )
        kwargs = {k:v if isinstance(v, str) else json.dumps(v) for k,v in kwargs.items()}
        return kwargs

    def push_page(self, idx):
        if not idx in self._cache or len(self._cache[idx]):
            return
        self._cache[idx].push()

    def get_page(self, idx):
        if idx not in self._cache or not len(self._cache[idx]):
            self.pull_page(idx)
        return self._cache.get(
            idx, EvePage(name="Place holder", fields=self.fields))

    def get_page_records(self, idx):
        return self.get_page(idx).to_records()

    def get_page_df(self, idx, fields=None):
        df = self.get_page(idx).to_dataframe()
        # if "_id" in df.columns and set_index:
        #     df = df.set_index("_id")
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
                   "fields",
                   "sorting",
                   watch=True)
    def clear_cache(self):
        self._cache = EvePageCache()
        self._plot = None

    def reload_page(self, page_number=None):
        if page_number is None:
            page_number = self.page_number
        if page_number in self._cache:
            self._cache.pop(page_number)
        self.pull_page(page_number)
        self._cache = self._cache

    def remove_item(self, _id: str) -> bool:
        return self[_id].delete()

    def filter(self, **filters):
        """Filter resource, filters can be any valid mongodb query parameters.

        Returns:
            EveResource: Filtered resource.
        """
        filtered = self.clone(filters=filters)
        filtered.clear_cache()
        return filtered

    def project(self, *fields, **projection):
        """Project resource (only fetch some of the fields.)

        Raises:
            ValueError: raised if passed inconsistent projections.

        Returns:
            EveResource: Projected resource.
        """
        projections ={col:1 for col in fields if col in self.schema}
        projections.update(projection)
        value_sum = sum(list(projections.values()))
        if value_sum==0:
            fields = [c for c in self.schema if c not in projections]
        elif value_sum==len(projections):
            fields = list(projections)
        else:
            raise ValueError("Mongo projections can either be inclusive or exclusive but not both.")
        projected =  self.clone(fields=fields)
        # projected.clear_cache()
        return projected

    def sort(self, *fields):
        """Sort data by given fields,
                     fields starting with `-` will be sorted in descending order.
        """
        sorted_ = self.clone(sorting=[col for col in fields if col in self.sorting_options])
        # sorted_.clear_cache()
        return sorted_

    def paginate(self, page_size: int):
        """Change how many items will be in each page.

        Args:
            page_size (int): number of items per page

        Returns:
            EveResource: Paginated EveResource
        """
        paginated = self.clone(items_per_page=page_size)
        
        return paginated

    def pprint_schema(self):
        """Pretty print the schema in nice yaml format 
        """
        print(yaml.dump(self.schema))

    def clone(self, **kwargs):
        c = super().clone(**kwargs)
        c.clear_cache()
        return c

    @property
    def plot(self):
        """
        Shamelessly copied from the amazing Intake package and modified slightly.
        Returns a hvPlot object to provide a high-level plotting API. Will use Dask
        if available, reading parralelism is set by page size and then data is repartitioned by number 
        of cpus available. small collections are pre-read and converted to regular pandas dataframe.
        To display in a notebook, be sure to run ``panel_eve.output_notebook()``
        first.
        """
        if not self.is_table:
            raise TypeError("Plotting API currently only supports tabular data.")

        if self._plot is None:
            try:
                from hvplot import hvPlot
            except ImportError:
                raise ImportError("The eve_panel plotting API requires hvplot."
                                "hvplot may be installed with:\n\n"
                                "`conda install -c pyviz hvplot` or "
                                "`pip install hvplot`.")
            try:
                import dask
                nitems = self.nitems
                # persist = self.nitems<1500
                data = self.to_dask(persist=True, clone=False)
                data = data.repartition(npartitions=min(data.npartitions, mp.cpu_count()))
                if nitems<2000:
                    data = data.compute()
            except ImportError:
                data = self.df
            metadata = self.metadata.get('plot', {})
            fields = self.metadata.get('fields', {})
            for attrs in fields.values():
                if 'range' in attrs:
                    attrs['range'] = tuple(attrs['range'])
            metadata['fields'] = fields
            plots = self.metadata.get('plots', {})
            self._plot = hvPlot(data, custom_plots=plots, **metadata)
        return self._plot

    @property
    def plots(self):
        return list(self.metadata.get('plots', {}))

    @param.depends("_url")
    def upload_view(self):
        clear_button = pn.widgets.Button(name="Clear buffer",
                                         button_type="warning",
                                         width_policy='max',
                                         sizing_mode=self.sizing_mode,
                                         width=int(self.max_width/4),
                                         max_width=int(self.max_width/3),
                                         )
        clear_button.on_click(lambda event: self.clear_upload_buffer())

        upload_file = pn.widgets.FileInput(accept=",".join(
            [f".{ext}" for ext in FILE_READERS]),
                                           width=int(self.max_width/4),
                                           max_width=int(self.max_width/3),
                                           )
        upload_file.link(self, filename="_filename", value="_file_buffer")
        upload_file_button = pn.widgets.Button(name="Read file",
                                               button_type="primary",
                                               width_policy='max',
                                               sizing_mode=self.sizing_mode,
                                               width=int(self.max_width/4),
                                               max_width=int(self.max_width/3),
                                               )
        upload_file_button.on_click(lambda event: self._read_file_buffer())

        upload_button = pn.widgets.Button(name="Insert to DB",
                                          button_type="success",
                                          width_policy='max',
                                          sizing_mode=self.sizing_mode,
                                          width=int(self.max_width/4),
                                          max_width=int(self.max_width/3),
                                          )
        upload_button.on_click(lambda event: self.flush_buffer())
        read_clipboard_button = pn.widgets.Button(name="Read Clipboard",
                                                  button_type="primary",
                                                  width_policy='max',
                                                  sizing_mode=self.sizing_mode,
                                                  width=int(self.max_width/4),
                                                  max_width=int(self.max_width/3),
                                                  )
        read_clipboard_button.on_click(lambda event: self.read_clipboard())

        validate_button = pn.widgets.Button(name="Validate",
                                                  button_type="primary",
                                                  width_policy='max',
                                                  sizing_mode=self.sizing_mode,
                                                  width=int(self.max_width/4),
                                                  )
        validate_button.on_click(lambda event: self.flush_buffer(dry=True))

        first_row_buttons = pn.Row(upload_file, upload_file_button, read_clipboard_button)
        second_row_buttons = pn.Row(validate_button, clear_button, upload_button)
        input_buttons = pn.Column(first_row_buttons, second_row_buttons)
        upload_view = pn.Column(self.paste_bin, input_buttons,"### Errors:",  self.upload_errors_view)
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
            pn.pane.Alert(err, alert_type="danger",
            margin=2,
            width_policy='max',
            sizing_mode=self.sizing_mode,
            width=self.max_width-30,
            max_width=self.max_width,
            )
            for err in self.upload_errors
        ]
        return pn.Column(*alerts,
                         scroll=True,
                         max_height=300,
                         width_policy='max',
                         sizing_mode=self.sizing_mode,
                         max_width=self.max_width-30)

    @param.depends("current_page")
    def download_view(self):
        # data_selection = pn.widgets.RadioBoxGroup(options=["Current Page", "Range"])
        # page_range = pn.widgets.IntRangeSlider()
        page_num_select = pn.widgets.IntInput(name="Page", value=self.page_number, step=1, start=1, end=int(1e6))
        def cb():
            page = self.get_page(page_num_select.value)
            return page.to_file()
        download_button = pn.widgets.FileDownload(callback=cb, label="Download JSON", filename=f'{self.name}_page{page_num_select.value}.json')
        return pn.Column(page_num_select, download_button )

    @param.depends("_plot_selection")
    def selected_plot_view(self):
        if self._plot_selection in self.plots:
            plot = getattr(self.plot, self._plot_selection)()
            return pn.panel(plot)
        else:
            return pn.Column("# No plot selected.")

    def make_panel(self, show_client=True, tabs_location='above'):
        plot_selector = pn.Param(self.param._plot_selection,
        widgets={"_plot_selection":{"type": pn.widgets.Select,
                                    "options": ["None"]+self.plots}},
                                width_policy='max',
                                sizing_mode='stretch_width',
                                width=int(self.max_width/4),
                                max_width=int(self.max_width/3),
                                )
        plotting = pn.Column(plot_selector,
                             self.selected_plot_view,
                             width_policy='max',
                             sizing_mode='stretch_width',
                             max_width=int(self.max_width - 30),
                             )

        column_select = pn.Param(self.param.fields,
                            width_policy='max',
                            sizing_mode='stretch_width',
                            max_width=int(self.max_width - 30),
                            widgets={
                                "fields": {
                                    "type": pn.widgets.MultiChoice,
                                    "options": self.field_options,
                                    "width": int(self.max_width - 30)
                                }
                            })

        sorting_select = pn.Param(self.param.sorting,
                            width_policy='max',
                            sizing_mode='stretch_width',
                            max_width=int(self.max_width - 30),
                            widgets={
                                "sorting": {
                                    "type": pn.widgets.MultiChoice,
                                    "options": self.sorting_options,
                                    "width": int(self.max_width - 30)
                                }
                            })

        page_settings = pn.Column(pn.Row(self.param.items_per_page,
                                         self.param.filters,
                                         self.param._page_view_format,
                                         width_policy='max',
                                         sizing_mode=self.sizing_mode,
                                         max_width=int(self.max_width - 50)),
                                  column_select,
                                  sorting_select,
                                  max_width=int(self.max_width - 10))
        if show_client:
            page_settings.append("### HTTP client")
            page_settings.append(pn.layout.Divider())
            page_settings.append(self._http_client.panel)


        tabs = pn.Tabs(
                ("Data", self.current_page_view),
                ("Plots", plotting),
                ("Upload", self.upload_view()),
                ("Download", self.download_view),
                ("Config", page_settings),
                ("Errors", self._http_client.messages),
                dynamic=False,
                tabs_location=tabs_location,
                width_policy='max',
                sizing_mode=self.sizing_mode,
                max_width=self.max_width-20,
            )

        buttons = pn.Param(self.param,
                           parameters=[
                               "_prev_page_button", "page_number",
                               "_reload_page_button", "_next_page_button",
                               "_clear_cache_button",
                           ],
                           default_layout=pn.Row,
                           name="",
                           width_policy='max',
                           sizing_mode=self.sizing_mode,
                           width=int(self.max_width/2),
                           min_width=300,
                           max_width=int(self.max_width/1.5))

        header = pn.Row(
            f'## {self.name.replace("_", " ").title()} resource',
            pn.Spacer(sizing_mode='stretch_both'),
            buttons,
            pn.Spacer(sizing_mode='stretch_both'),
            
        )
        if settings.SHOW_INDICATOR:
            header.append(self._http_client.busy_indicator)

        view = pn.Column(
            header, 
            tabs,
            width_policy='max',
            sizing_mode=self.sizing_mode,
            width=self.max_width-20,
            max_width=self.max_width,
            max_height=self.max_height,
            )

        return view
    