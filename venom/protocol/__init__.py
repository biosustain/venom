from abc import ABCMeta, abstractmethod
from base64 import b64encode, b64decode
from functools import partial
from json import JSONDecodeError
from typing import Type, TypeVar, Generic, Callable, Union, Any, Tuple, Iterable, Dict, List

from venom import Empty
from venom import Message
from venom.exceptions import ValidationError
from venom.fields import Field, ConverterField, RepeatField, FieldDescriptor


class Protocol(metaclass=ABCMeta):
    mime = None  # type: str
    name = None  # type: str

    def __new__(cls, fmt: Type[Message]):
        try:
            return fmt.__meta__.protocols[cls.name]
        except KeyError:
            instance = super(Protocol, cls).__new__(cls)
            instance.__init__(fmt)
            return instance

    def __init__(self, fmt: Type[Message]):
        fmt.__meta__.protocols[self.name] = self
        self._format = fmt

    @classmethod
    def _get_protocol(cls, fmt: Type[Message]):
        try:
            return fmt.__meta__.protocols[cls.name]
        except KeyError:
            return cls(fmt)

    @abstractmethod
    def pack(self, message: Message, include: Iterable[str] = None) -> bytes:
        pass

    @abstractmethod
    def unpack(self, buffer: bytes, include: Iterable[str] = None) -> Message:
        pass


try:
    import ujson as json
except ImportError:
    import json

JSONPrimitive = Union[str, int, float, bool]

JSONValue = Union[JSONPrimitive, Dict[str, JSONPrimitive], List[JSONPrimitive]]


class DictProtocol(Protocol, metaclass=ABCMeta):

    @abstractmethod
    def encode(self, message: Message, include: Iterable[str] = None):
        pass

    @abstractmethod
    def decode(self, instance: Any, include: Iterable[str] = None) -> Message:
        pass


class JSON(DictProtocol):
    mime = 'application/json'
    name = 'json'

    def __init__(self, fmt: Type[Message]):
        super().__init__(fmt)
        self.field_encoders = {key: self._field_encoder(field) for key, field in fmt.__fields__.items()}
        self.field_decoders = {key: self._field_decoder(field) for key, field in fmt.__fields__.items()}

    T = TypeVar('T')

    @staticmethod
    def _cast(type_: Type[T], value: Any) -> T:
        # TODO JSON type names, i.e. object instead of dict, integer instead of int etc.
        if not isinstance(value, type_):
            raise ValidationError("{} is not of type '{}'".format(repr(value), type_.__name__))
        return value

    @staticmethod
    def _cast_number(value: Any):
        if type(value) not in (int, float):
            raise ValidationError("{} is not a number".format(value))
        return float(value)

    def _field_encoder(self, field: FieldDescriptor) -> Callable[[Any], JSONValue]:
        if isinstance(field, RepeatField):
            field_item_encoder = self._field_encoder(field.items)
            return lambda lst: [field_item_encoder(item) for item in lst]

        if not isinstance(field, Field):
            raise NotImplementedError()

        if issubclass(field.type, Message):
            field_protocol = self._get_protocol(field.type)
            return lambda msg: field_protocol.encode(msg)

        if field.type is bytes:
            return lambda b: b64encode(b)

        # assume all is JSON from here
        return lambda value: value

    def _field_decoder(self, field: FieldDescriptor) -> Callable[[JSONValue], Any]:
        if isinstance(field, RepeatField):
            field_item_decoder = self._field_decoder(field.items)
            return lambda lst: [field_item_decoder(item) for item in self._cast(list, lst)]

        if not isinstance(field, Field):
            raise NotImplementedError()

        if issubclass(field.type, Message):
            field_protocol = self._get_protocol(field.type)
            return lambda msg: field_protocol.decode(msg)

        # an integer (int) in JSON is also a number (float), so we convert here if necessary:
        if field.type is float:
            return self._cast_number

        if field.type is bytes:
            # TODO catch TypeError
            return lambda b: b64decode(b)

        return partial(self._cast, field.type)

    def encode(self, message: Message, include: Iterable[str] = None):
        obj = {}
        for name, value in message.items():
            if include is not None and name in include:
                continue
            obj[name] = self.field_encoders[name](value)
        return obj

    def decode(self, instance: Any, include: Iterable[str] = None) -> Message:
        instance = self._cast(dict, instance)
        message = self._format()

        for name, decode in self.field_decoders.items():
            if name in instance and (include is None or name in include):
                try:
                    message[name] = decode(instance[name])
                except ValidationError as e:
                    e.path.insert(0, name)
                    raise e
        return message

    # TODO include It
    def pack(self, message: Message, include: Iterable[str] = None) -> bytes:
        if self._format is Empty:
            return b''
        return json.dumps(self.encode(message)).encode('utf-8')

    def unpack(self, buffer: bytes, include: Iterable[str] = None):
        # special case for 'Empty' message (may be 0-length/empty)
        if self._format is Empty and len(buffer) == 0:
            return self._format()

        try:
            return self.decode(json.loads(buffer.decode('utf-8')), include)
        except (ValueError, JSONDecodeError) as e:
            raise ValidationError("Invalid JSON: {}".format(str(e)))


def _cast(type_: type, value: Any):
    # TODO JSON/wire-format specific type names, i.e. object instead of dict, integer instead of int etc.
    try:
        return type_(value)
    except ValueError:
        raise ValidationError("{} is not formatted as a '{}'".format(repr(value), type_.__name__))


def string_decoder(field: Field, protocol: Type[Protocol]):
    # TODO support converter fields and message fields (unpack message using protocol)
    if field.type in (int, str):
        return lambda value: _cast(field.type, value)
    # TODO support boolean etc. (with wire formats that allow it)
    raise NotImplementedError('Unable to resolve {} from strings'.format(field))
