import ast
import json
import base64

import panel as pn
import param
from eve.io.mongo.validation import Validator
from panel.widgets import LiteralInput


class LiteralSchemaInputBase(LiteralInput):
    """[summary]

    Args:
        LiteralInput ([type]): [description]
    """
    def validate_schema(self, value):
        return True

    def _process_property_change(self, msg):
        msg = super(LiteralSchemaInputBase, self)._process_property_change(msg)
        if msg['value'] == self.value:
            return msg
        new_state = ''
        if 'value' in msg:
            value = msg.pop('value')
            if not self.validate_schema(value):
                new_state = ' (invalid)'
                value = self.value
            msg['value'] = value
            msg['name'] = msg.get('title', self.name).replace(
                self._state, '').replace(new_state, '') + new_state
            self._state = new_state
            self.param.trigger('name')
        return msg


def LiteralSchemaInput(name, schema, type_=None):
    validator = Validator({"value": schema})

    def validate_schema(self, value):
        return validator.validate({"value": value})

    params = {
        "validate_schema": validate_schema,
        "type": type_,
    }
    return type(name + "InputWidget", (LiteralSchemaInputBase, ), params)


def PDFViewer(pdf, width=800, height=500):
    if isinstance(pdf, bytes):
        pdf = base64.b64encode(pdf).decode()
    return pn.pane.HTML(f'<iframe width={width} height={height} src="data:application/pdf;base64,{pdf}" type="application/pdf"></iframe>',
                   width=1000,sizing_mode="stretch_both")

def PNGViewer(png, width=800, height=500):
    if isinstance(png, bytes):
        png = base64.b64encode(png).decode()
    src = f"data:image/png;base64,{png}"
    return pn.pane.HTML(f"<img src='{src}' width={width} height={height}></img>")
                
class FileInputPreview(pn.widgets.FileInput):

    @param.depends('value')
    def preview(self):
        if not self.filename:
            return pn.Column()
        if self.filename.endswith(".png"):
            return PNGViewer(self.value)
        elif self.filename.endswith(".pdf"):
            return PDFViewer(self.value)

    def _repr_mimebundle_(self, include=None, exclude=None):
        return pn.Column(self, self.preview)

WIDGET_MAPPING = {
    "media": {"type": pn.widgets.FileInput, "align": "end"},
}


def get_widget(name, schema):
    if schema["type"] == "dict" and "schema" in schema:
        return LiteralSchemaInput(name, schema, dict)
    elif schema["type"] == "list" and "schema" in schema:
        return LiteralSchemaInput(name, schema, list)
    else:
        return WIDGET_MAPPING.get(schema["type"], None)
