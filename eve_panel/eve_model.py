"""
Eve model
==========
Base classes for objects that represent Eve models.
"""

import panel as pn
import param

from . import settings


class DefaultLayout(pn.GridBox):
    ncols = param.Integer(max(1, int(settings.GUI_WIDTH / 200)))
    width = param.Integer(settings.GUI_WIDTH)


class EveModelBase(param.Parameterized):
    _panel = param.ClassSelector(pn.viewable.Viewable,
                                 default=None,
                                 precedence=-1)

    def make_panel(self):
        parameters = [
            k for k, v in self.params().items() if not k.startswith("_")
        ]
        panel = pn.Param(self.param,
                         width=settings.GUI_WIDTH,
                         parameters=parameters,
                         default_layout=pn.Card)
        return panel

    def panel(self):
        # return self.make_panel()
        if self._panel is None:
            self._panel = pn.panel(self.make_panel)
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
        params = dict(self.param.get_param_values())
        params.update(kwargs)
        return self.__class__(**params)