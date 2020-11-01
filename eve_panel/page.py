from io import BytesIO, StringIO

import pandas as pd
import panel as pn
import param

from . import settings
from .eve_model import EveModelBase
from .http_client import DEFAULT_HTTP_CLIENT, EveHttpClient
from .item import EveItem


class EvePage(EveModelBase):
    _columns = param.List(default=["_id"])
    _items = param.Dict(default={})

    def __getitem__(self, key):
        return self._items[key]

    def __setitem__(self, key, value):
        self._items[key] = value

    def __contains__(self, key):
        return key in self._items

    def __len__(self):
        return len(self._items)

    def __bool__(self):
        return bool(len(self))

    @property
    def df(self):
        return self.to_dataframe()

    def keys(self):
        yield from self._items.keys()

    def values(self):
        yield from self._items.values()

    def items(self):
        yield from self._items.items()

    def to_records(self):
        return [item.to_dict() for item in self.values()]

    def records(self):
        for item in self.values():
            yield item.to_dict()

    def to_dataframe(self):
        df = pd.DataFrame(self.to_records(), columns=self._columns)
        if "_id" in df.columns:
            df = df.set_index("_id")
        return df

    def push(self, names=None):
        if names is None:
            names = self.keys()
        for name in names:
            self._items[name].push()

    def pull(self, names=None, version=1):
        if names is None:
            names = self.keys()
        for name in names:
            self._items[name].pull(version=version)

    @param.depends("_items")
    def widgets_view(self):
        if not len(self._items):
            return pn.Column("## No items to display.")

        items = [(item.name, item.panel()) for item in self._items.values()]
        view = pn.Tabs(*items,
                       dynamic=True,
                       height=int(settings.GUI_HEIGHT - 10),
                       width=settings.GUI_WIDTH)
        return view

    @param.depends("_items")
    def table_view(self):
        if not len(self._items):
            return pn.Column("## No items to display.")
        df = self.to_dataframe()
        return pn.widgets.DataFrame(df,
                                    disabled=True,
                                    width=settings.GUI_WIDTH,
                                    height=int(settings.GUI_HEIGHT - 30))

    @param.depends("_items")
    def json_view(self):
        return pn.pane.JSON(self.to_records(),
                            theme="light",
                            width=settings.GUI_WIDTH,
                            height=int(settings.GUI_HEIGHT - 30))

    def panel(self):
        tabs = pn.Tabs(("Table", self.table_view),
                       ("Widgets", self.widgets_view),
                       ("JSON", self.json_view),
                       height=int(settings.GUI_HEIGHT),
                       width=settings.GUI_WIDTH,
                       dynamic=True)
        return pn.Column(f"## {self.name}", tabs)


class PageZero(EvePage):
    @param.depends("_items")
    def widgets_view(self):
        return self.panel()

    @param.depends("_items")
    def table_view(self):
        return self.panel()

    @param.depends("_items")
    def json_view(self):
        return self.panel()

    def panel(self):
        return pn.Column(
            pn.layout.Divider(width=settings.GUI_WIDTH),
            "### You are on the landing page for this resource, no data here.",
            "TIP 1: Use the \u23E9 button to load the first page.",
            "TIP 2: You can use the settings tab to change what data is loaded and how it is displayed.",
            "TIP 3: If you just want to upload data, you can go directly to the upload tab.",
            pn.layout.Divider(width=settings.GUI_WIDTH),
            width=settings.GUI_WIDTH,
            height=300,
        )


class EvePageCache(param.Parameterized):
    _pages = param.Dict(default={})

    def __getitem__(self, key):
        if isinstance(key, str):
            for page in self._pages.values():
                if key in page:
                    return page[key]
            else:
                raise KeyError
        elif isinstance(key, int):
            return self._pages[key]

    def __setitem__(self, key, value):
        self._pages[key] = value

    def __contains__(self, key):
        if isinstance(key, str):
            for page in self._pages.values():
                if key in page:
                    return True
            else:
                return False
        return key in self._pages

    def get(self, key, fallback=None):
        return self._pages.get(key, fallback)

    def keys(self):
        yield from self._pages.keys()

    def values(self):
        yield from self._pages.values()

    def items(self):
        yield from self._pages.items()
