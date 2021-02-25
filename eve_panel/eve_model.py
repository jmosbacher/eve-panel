"""
Eve model
==========
Base classes for objects that represent Eve models.
"""

import panel as pn
import param
from copy import copy

from .settings import config as settings


class DefaultLayout(pn.GridBox):
    ncols = param.Integer(max(1, int(settings.GUI_WIDTH / 200)))
    width = param.Integer(settings.GUI_WIDTH)


class EveModelBase(param.Parameterized):
    _panel = param.ClassSelector(pn.viewable.Viewable,
                                 default=None,
                                 precedence=-1)
    max_width = param.Integer(default=settings.GUI_WIDTH, precedence=-1)
    max_height = param.Integer(default=settings.GUI_HEIGHT, precedence=-1)
    sizing_mode = param.Selector(default=settings.SIZING_MODE, precedence=-1, objects=["stretch_width", 
                                "stretch_height", "stretch_both", "scale_width", "scale_height", "scale_both"])

    def make_panel(self):
        parameters = [
            k for k, v in self.param.get_param_values()
             if not k.startswith("_") and not isinstance(v,bytes)]
        panel = pn.Param(self.param,
                         max_width=self.max_width,
                         max_height=self.max_height,
                         sizing_mode=self.sizing_mode,
                         parameters=parameters,
                         default_layout=pn.Card)
        return panel

    def panel(self):
        if self._panel is None:
            self._panel = self.make_panel()
        return self._panel

    def _repr_mimebundle_(self, include=None, exclude=None):
        mimebundle = self.panel()._repr_mimebundle_(include, exclude)
        return mimebundle

    @property
    def gui(self):
        return self.panel()

    def show(self):
        return self.panel().show()

    def servable(self):
        return self.panel().servable()

    def clone(self, **kwargs):
        params = {}
        for k,v in self.param.get_param_values():
            if isinstance(v, EveModelBase):
                try:
                    params[k] = v.clone()
                except:
                    params[k] = v
            else:
                try:
                    params[k] = copy(v)
                except:
                    params[k] = v
        params.update(kwargs)
        params["_panel"] = None
        return self.__class__(**params)

    def propagate(self, **kwargs):
        for k,v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
        for k,v in self.param.get_param_values():
            if isinstance(v, EveModelBase):
                v.propagate(**kwargs)
        self._panel = None
        return self

    def __iter__(self):
        for k,v in self.param.get_param_values():
            if isinstance(v, EveModelBase):
                v = dict(v)
            yield k,v

    def __getstate__(self):
        state = super().__getstate__()
        state.pop("_panel", None)
        return state

    def __repr__(self):
        return self.name