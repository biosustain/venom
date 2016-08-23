from typing import Any, Union

from collections.abc import Mapping

from jsonschema import Draft4Validator
from jsonschema import FormatChecker
from jsonschema import ValidationError

from venom.fields import Field, MapField, RepeatField, ConverterField
from venom.message import Message
from venom.types import int64, int32, float32, float64


class JSONSchemaValidator(object):
    def __init__(self):
        self._message_schemas = {}
        self._message_validators = {}

    # def validate_field(self, instance: Any, field: Union[Field, MapField, RepeatField]):
    #     pass

    def validate(self, instance: Any, cls: type(Message)):
        try:
            validator = self._message_validators[cls]
        except KeyError:
            validator = self._message_validators[cls] = self._validator(cls)

        try:
            validator.validate(instance)
        except ValidationError as ve:
            raise ve

    # errors = validator.iter_errors(instance)
    # raise ValidationError(errors)

    def _field_schema(self, field: Union[Field, MapField, RepeatField]):
        if isinstance(field, RepeatField):
            schema = {
                "type": "array",
                "items": self._field_schema(field.items)
            }
        elif isinstance(field, MapField):
            schema = {
                "type": "object",
                "properties": self._field_schema(field.values),
                "additionalProperties": False
            }
        elif isinstance(field, ConverterField):
            return self._message_schema(field.converter.wire)
        elif issubclass(field.type, Message):
            return self._message_schema(field.type)
        elif field.type == str:
            schema = {"type": "string"}
        elif field.type in (int, int32, int64):
            schema = {"type": "integer"}
        elif field.type in (float, float32, float64):
            schema = {"type": "number"}
        elif field.type == bool:
            schema = {"type": "boolean"}
        else:
            raise ValueError("Unsupported field type: '{}'".format(field.type))

        # TODO support enum.Enum!

        for check in field.checks:
            schema.update(check.schema())
        return schema

    def _message_schema(self, cls: type(Message)):
        if cls in self._message_schemas:
            return self._message_schemas[cls]

        schema = {
            "type": "object",
            "properties": {field.attribute: self._field_schema(field) for field in cls.__fields__.values()},
            "additionalProperties": True  # messages may always have additional properties
        }

        required = [field.attribute for field in cls.__fields__.values() if not field.optional]

        if required:
            schema['required'] = required

        Draft4Validator.check_schema(schema)
        self._message_schemas[cls] = schema
        return schema

    def _validator(self, cls: type(Message)):
        # TODO OpenAPI FormatChecker implementation
        return Draft4Validator(self.schema(cls), format_checker=FormatChecker())

    def schema(self, cls: type(Message)):
        return self._message_schema(cls)


