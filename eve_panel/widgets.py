import ast
import json

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


WIDGET_MAPPING = {
    "media": pn.widgets.FileInput,
}


def get_widget(name, schema):
    if schema["type"] == "dict" and "schema" in schema:
        return LiteralSchemaInput(name, schema, dict)
    elif schema["type"] == "list" and "schema" in schema:
        return LiteralSchemaInput(name, schema, list)
    else:
        return WIDGET_MAPPING.get(schema["type"], None)
