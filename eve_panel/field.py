import param
from eve.io.mongo.validation import Validator

from .types import COERCERS


SUPPORTED_SCHEMA_FIELDS = [
    "type",
    "schema",
    "required",
    "default",
    "readonly",
    "valueschema",
    "keyschema",
    "regex",
    "minlength",
    "maxlength",
    "min",
    "max",
    "allowed",
    "items",
    "empty",
    "nullable",
]

TYPE_MAPPING = {
    "media": "binary",
}

def EveField(name, schema, klass):
    if isinstance(klass, param.ClassSelector):
        return klass
    if not isinstance(klass, type):
        return klass
    schema = {k: v for k, v in schema.items() if k in SUPPORTED_SCHEMA_FIELDS}
    if schema["type"] in COERCERS:
        schema["coerce"] = COERCERS[schema["type"]]
    if schema["type"] in TYPE_MAPPING:
        schema["type"] = TYPE_MAPPING[schema["type"]]
    

    # validator = Validator({"value": schema})

    def _validate(self, val):
        if self.allow_None and val is None:
            return

        if self.owner is None:
            return

        if self.name is None:
            return

        try:
            if not self.validator.validate({"value": val}):
                sep = "\n"
                errors = [
                    f"Cannot set \'{self.owner.name}.{self.name}\' to \'{val}\' of type {type(val)}."
                ]
                for k, v in self.validator.errors.items():
                    errors.append(f"{k} {v}")
                if len(errors) <= 2:
                    sep = ". "
                raise ValueError(" ".join(errors))
        except ValueError:
            raise
        except Exception:
            pass
 

    params = {
        # "_schema": schema,
        "_validate": _validate,
        "validator": Validator({"value": schema})
    }

    return type(f"Eve{name.title()}{klass.__name__}Field", (klass, ), params)

