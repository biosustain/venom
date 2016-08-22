import json
from abc import ABCMeta, abstractmethod
from typing import Any, Union

from venom.fields import FieldDescriptor, RepeatField, MapField, ConverterField, Field
from venom.message import Message, Empty
from venom.types import float32, float64


class WireFormat(metaclass=ABCMeta):
    mime = None  # type: str

    @abstractmethod
    def pack(self, fmt: type(Message), message: Message) -> bytes:
        pass

    @abstractmethod
    def unpack(self, fmt: type(Message), buffer: bytes) -> Message:
        pass


class JSON(WireFormat):
    mime = 'application/json'

    # TODO support ujson and other encoders/decoders.
    def __init__(self):
        pass

    def encode(self, message: Message, cls: type(Message) = None) -> Any:

        # TODO special encoding/decoding for e.g. Value, Empty messages

        msg = {}
        for key, field in (cls or message).__fields__.items():
            if field.attribute in message:
                msg[field.attribute] = self.encode_field(message[field.attribute], field)
        return msg

    def encode_field(self, value: Any, field: Union[Field, MapField, RepeatField]):
        # XXX value should never be none.
        if value is None:
            return None

        if isinstance(field, RepeatField):
            return [self.encode_field(item, field.items) for item in value]
        if isinstance(field, MapField):
            return {k: self.encode_field(v, field.values) for k, v in value.items()}
        if isinstance(field, ConverterField):
            return self.encode(field.converter.format(value))

        if issubclass(field.type, Message):
            return self.encode(value)

        # assumes all is JSON from here
        return value

    def decode(self, instance: Any, cls: type(Message)) -> Message:
        # TODO schema validation here.

        # TODO special encoding/decoding for e.g. Value, Empty messages

        if not isinstance(instance, dict):
            raise ValueError()

        message = cls()
        for key, field in cls.__fields__.items():
            if field.attribute not in instance:
                if not field.optional:
                    raise ValueError()
            else:
                message[field.attribute] = self.decode_field(instance[field.attribute], field)

        # NOTE additional properties are simply ignored for forward compatibility.
        # TODO one_of() validation: simply picks first match.
        return message

    def decode_field(self, instance: Any, field: Union[Field, MapField, RepeatField]):
        if instance is None:
            return None

        if isinstance(field, RepeatField):
            assert isinstance(instance, (set, list, tuple))
            return [self.decode_field(item, field.items) for item in instance]
        if isinstance(field, MapField):
            assert isinstance(instance, dict)
            return {key: self.decode_field(value, field.values) for key, value in instance.items()}
        if isinstance(field, ConverterField):
            return field.converter.convert(self.decode(instance, field.converter.wire))
        if issubclass(field.type, Message):
            return self.decode(instance, field.type)

        # an integer (int) in JSON is also a number (float), so we convert here if necessary:
        if type(instance) == int and field.type in (float, float32, float64):
            return float(instance)

        # assumes all is JSON from here
        return instance

    def pack(self, fmt: type(Message), message: Message) -> bytes:
        return json.dumps(self.encode(message, cls=fmt)).encode('utf-8')

    def unpack(self, fmt: type(Message), value: bytes):
        # TODO catch JSONDecodeError
        return self.decode(json.loads(value.decode('utf-8')), cls=fmt)

    # packb and pack


# TODO special URL wire format for decoding request parameters
