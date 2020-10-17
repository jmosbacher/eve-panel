
import param
import panel as pn
import pandas as pd
import json
import itertools

from .eve_model import EveModelBase
from .item import EveItem
from .client import EveApiClient, default_client
from . import settings

def items_to_df(items):
    return pd.DataFrame([item.to_dict() for item in items])


class EveResource(EveModelBase):
    _client = param.ClassSelector(EveApiClient, precedence=-1)
    _url = param.String(precedence=-1)
    _page_data = param.List(precedence=-1)
    _resource = param.Dict(default={}, constant=True, precedence=-1)
    _schema = param.Dict(default={}, constant=True, precedence=-1)
    _cache = param.Dict(default={}, precedence=-1)
    _page_cache = param.Dict(default={}, precedence=-1)
    _item_class = param.ClassSelector(EveItem, is_instance=False, precedence=-1)
    selection = param.ListSelector(default=[], objects=[], precedence=-1)
    
    filters = param.Dict(default={}, doc="Filters")
    projection = param.Dict(default={}, doc="Projections")

    max_results = param.Integer(default=25, label="Items per page", precedence=0)
    _prev_page_button = param.Action(lambda self: self.previous_page(), label="<<", precedence=1)
    page_number = param.Integer(default=1, label="", doc="Page number", precedence=2)
    _next_page_button = param.Action(lambda self: self.next_page(), label=">>", precedence=3)
    
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
        )
        return cls(**params)

    def __getitem__(self, key):
        if key in self._cache:
            return self._cache[key]
        data = self._client.get("/".join(self.url, key))
        if data:
            item = self._item_class(data)
            self[key] = item
            return item
        raise KeyError
    
    def __setitem__(self, key, value):
        self._cache[key] = value
        self.param.selection.objects = self._cache
    
    @param.depends("selection")
    def selection_view(self):
        if not self.selection:
            return pn.pane.Markdown("## No items selected.")
        return pn.GridBox(*[item.panel() for item in self.selection], ncols=2)
    
    @param.depends("page_number")
    def page_view(self):
        return pn.GridBox(*[item.panel() for item in self._page_cache[self.page_number]], ncols=2)

    @param.depends("_cache")
    def selector_view(self):
        return pn.Param(self.param, parameters=["selection"], name=self._resource["resource_title"],
            widgets={"selection": { "type": pn.widgets.MultiSelect, 
                                    "height": 15*len(self._schema), 
                                    "width": int(0.8*settings.GUI_WIDTH)}} )

    @param.depends("page_number")
    def dataframe_view(self):
        # self._page_data = self.to_df()
        df = self.get_page_df(self.page_number)
        return pn.widgets.DataFrame(df, width=settings.GUI_WIDTH, height=int(settings.GUI_HEIGHT-30))

    @param.depends("selection")
    def panel(self):
        column_select = pn.widgets.MultiChoice(name="Columns", value=list(self._schema),
                             options=list(self._schema), width=int(settings.GUI_WIDTH))
        column_select.link(self.projection, callbacks={'value': self._update_projection})
        query_params = pn.Param(self.param, parameters=["filters",],
                                 default_layout=pn.Column, name="", width=int(settings.GUI_WIDTH))
        buttons = pn.Param(self.param, parameters=["_prev_page_button", "page_number", "_next_page_button"],
                             default_layout=pn.Row, name="", width=int(settings.GUI_WIDTH/3))
        page_settings = pn.Column(pn.Row(self.param.max_results, self.param.filters), column_select)
        # controls = pn.Row(pn.Column(query_params, buttons, width=int(settings.GUI_WIDTH/2), height=int(settings.GUI_HEIGHT/2) ),
        #                      column_select, width=settings.GUI_WIDTH, height=int(settings.GUI_HEIGHT/2))
        page_view = pn.Column(
                        buttons,
                        self.dataframe_view,
                        width=settings.GUI_WIDTH,
                        height=int(settings.GUI_HEIGHT),
                        )
        return pn.Tabs(("Page browser", page_view), 
                        ("Settings", page_settings),
                        width=int(settings.GUI_WIDTH),
                        height=int(settings.GUI_HEIGHT+10), )
    
    def _update_projection(self, projection, event):
        self.projection = { k:1 for k in event.new }

    @property
    def gui(self):
        return pn.panel(self.panel)
    
    @property
    def df(self):
        return self.to_df()

    def keys(self):
        for page in itertools.count():
            items = self.find(projection={"_id":1}, max_results=5000, page=page)
            if not items:
                break
            for item in items:
                yield item._id

    def values(self):
        for page in itertools.count():
            items = self.find(page=page)
            if not items:
                break
            for item in items:
                yield item

    def items(self):
        for page in itertools.count():
            items = self.find(page=page)
            if not items:
                break
            for item in items:
                yield item._id, item

    def new_item(self, data={}):
        item = self.item_class(**data)
        self[item._id] = item

    def to_records(self):
        return [item.to_dict() for item in self.values()]
    
    def to_df(self):
        data = []
        try:
            data = pd.json_normalize(self.to_list())
        except Exception as e:
            print(e)
        df = pd.DataFrame(data, columns=list(self._schema))
        if "_id" in df.columns:
            df = df.set_index("_id")
        return df
    
    def pull(self):
        for page in itertools.count():
            items = self.find(page=page)
            if not items:
                break
            for item in items:
                self[item._id] = item
            self._page_cache[page] = items
            
    def push(self, names=None):
        if names is None:
            documents = list(self._cache)
        for name in names:
            self[name].push()

    def find(self, query={}, projection={}, max_results=25, page=1):
        resp = self._client.get(self._url, where=json.dumps(query),
                 projection=json.dumps(projection), max_results=max_results, page=page)
        if not resp:
            return []
        items = [self._item_class(**doc) for doc in resp["_items"]]
        for item in items:
            self[item._id] = item
        return items
    
    def find_df(self, query={}, projection={}, max_results=25, page=1):
        items = [item.to_dict() for item in self.find(query, projection, max_results=max_results, page=page)]
        df = pd.DataFrame(items)
        if "_id" in df.columns:
            df = df.set_index("_id")
        return df

    def add_data(self, data):
        if isinstance(data, dict):
            data = [data]
        docs = []
        for doc in data:
            if isinstance(doc, dict):
                docs.append(doc)
            elif isinstance(doc, EveItem):
                docs.append(doc.to_dict())
        self._client.post(self._url, docs)

    def pull_page(self, page=1):
        items = self.find(query=self.filters, projection=self.projection, 
                            max_results=self.max_results, page=page)
        for item in items:
            self[item._id] = item
        if items:
            self._page_cache[page] = items
            self._page_data = items

    def get_page(self, page):
        if page not in self._page_cache:
            self.pull_page(page)
        return self._page_cache.get(page, [])
    
    def get_page_df(self, page):
        df = pd.DataFrame(items_to_df(self.get_page(page)))
        if "_id" in df.columns:
            df = df.set_index("_id")
        return df

    def next_page(self):
        self.page_number = self.page_number + 1
        return self.current_page()

    def current_page(self):
        return self.get_page_df(self.page_number)

    def previous_page(self):
        if self.page_number > 1:
            self.page_number = self.page_number - 1
        return self.current_page()

    @param.depends("page_number", watch=True)
    def page_changed(self):
        self._page_data = self.get_page(self.page_number)

    @param.depends("max_results", "filters", "projection", watch=True)
    def query_settings_changed(self):
        self._page_cache = {}
        self.page_changed()
