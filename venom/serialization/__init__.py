from abc import ABCMeta, abstractmethod
from functools import partial
from json import JSONDecodeError
from typing import Type, TypeVar, Generic, Callable, Union, Any, Tuple, Iterable

from venom import Empty
from venom import Message
from venom.exceptions import ValidationError
from venom.fields import Field, ConverterField, RepeatField, FieldDescriptor


class WireFormat(metaclass=ABCMeta):
    mime = None  # type: str

    def __new__(cls, fmt: Type[Message]):
        try:
            return fmt.__meta__.wire_formats[cls]
        except KeyError:
            instance = super(WireFormat, cls).__new__(cls)
            instance.__init__(fmt)
            return instance

    def __init__(self, fmt: Type[Message]):
        self._cache_wire_format(fmt)
        self._format = fmt

    def _cache_wire_format(self, fmt):
        fmt.__meta__.wire_formats[self.__class__] = self

    @classmethod
    def _get_wire_format(cls, fmt: Type[Message]):
        try:
            return fmt.__meta__.wire_formats[cls]
        except KeyError:
            return cls(fmt)

    @abstractmethod
    def pack(self, message: Message) -> bytes:
        pass

    @abstractmethod
    def unpack(self, buffer: bytes, skip: Iterable[str] = ()) -> Message:
        pass


try:
    import ujson as json
except ImportError:
    import json


JSONPrimitive = Union[str, int, float, bool]


class JSON(WireFormat):
    mime = 'application/json'

    def __init__(self, fmt: Type[Message]):
        super().__init__(fmt)
        self.field_encoders = {field.attribute: self._field_encoder(field) for field in fmt.__fields__.values()}
        self.field_decoders = [(field.attribute, self._field_decoder(field)) for field in fmt.__fields__.values()]

    @staticmethod
    def _cast(type_: type, value: Any):
        # TODO JSON type names, i.e. object instead of dict, integer instead of int etc.
        if type(value) != type_:
            raise ValidationError("{} is not of type '{}'".format(repr(value), type_.__name__))
        return value

    @staticmethod
    def _cast_number(value: Any):
        if type(value) not in (int, float):
            raise ValidationError("{} is not a number".format(value))
        return float(value)

    def _field_encoder(self, field: FieldDescriptor) -> Callable[[Any], JSONPrimitive]:
        if isinstance(field, ConverterField):
            field_converter = field.converter
            field_wire_format = self._get_wire_format(field_converter.wire)
            return lambda value: field_wire_format.encode(field_converter.format(value))

        if isinstance(field, RepeatField):
            field_item_encoder = self._field_encoder(field.items)
            return lambda lst: [field_item_encoder(item) for item in lst]

        if issubclass(field.type, Message):
            field_wire_format = self._get_wire_format(field.type)
            return lambda msg: field_wire_format.encode(msg)

        # assume all is JSON from here
        return lambda value: value

    def _field_decoder(self, field: FieldDescriptor) -> Callable[[JSONPrimitive], Any]:
        if isinstance(field, ConverterField):
            field_converter = field.converter
            field_wire_format = self._get_wire_format(field_converter.wire)
            return lambda msg: field_converter.convert(field_wire_format.decode(msg))

        if isinstance(field, RepeatField):
            field_item_decoder = self._field_decoder(field.items)
            return lambda lst: [field_item_decoder(item) for item in self._cast(list, lst)]

        if issubclass(field.type, Message):
            field_wire_format = self._get_wire_format(field.type)
            return lambda msg: field_wire_format.decode(msg)

        # an integer (int) in JSON is also a number (float), so we convert here if necessary:
        if field.type is float:
            return self._cast_number

        return partial(self._cast, field.type)

    def encode(self, message: Message):
        obj = {}
        for attr, value in message.items():
            obj[attr] = self.field_encoders[attr](value)
        return obj

    def decode(self, instance: Any, skip: Iterable[str] = ()) -> Message:
        instance = self._cast(dict, instance)
        msg = self._format()

        for attr, decode in self.field_decoders:
            if attr in instance and attr not in skip:
                try:
                    msg[attr] = decode(instance[attr])
                except ValidationError as e:
                    e.path.insert(0, attr)
                    raise e
        return msg

    def pack(self, message: Message) -> bytes:
        if self._format is Empty:
            return b''
        return json.dumps(self.encode(message)).encode('utf-8')

    def unpack(self, buffer: bytes, skip: Iterable[str] = ()):
        # special case for 'Empty' message (may be 0-length/empty)
        if self._format is Empty and len(buffer) == 0:
            return self._format()

        try:
            return self.decode(json.loads(buffer.decode('utf-8')), skip)
        except (ValueError, JSONDecodeError) as e:
            raise ValidationError("Invalid JSON: {}".format(str(e)))
