import param
import panel as pn


class DefaultLayout(pn.GridBox):
    ncols = 2
    margin=15
    width = 600
    sizing_mode = "stretch_width"
    
class EveModelBase(param.Parameterized):
    _panel = param.ClassSelector(pn.viewable.Viewable, default=None)

    def make_panel(self):
        parameters = [k for k,v in self.params().items() if not k.startswith("_")]
        panel = pn.Param(self.param, width=600,
                                   parameters=parameters,
                                   default_layout=DefaultLayout)
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
    