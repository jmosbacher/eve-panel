import panel as pn
import param
from .eve_model import EveModelBase


class EveSchema(EveModelBase):
    _schema_def = param.Dict(constant=True)

    def to_dtype(self):
        pass
    
    def to_fields(self):
        pass

    def to_open_api(self):
        pass

    def to_item_class(self):
        pass
    
    def validate(self, doc):
        pass