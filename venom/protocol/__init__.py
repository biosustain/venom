from abc import ABCMeta, abstractmethod
from base64 import b64encode, b64decode
from functools import partial
from json import JSONDecodeError
from typing import Type, TypeVar, Generic, Callable, Union, Any, Tuple, Iterable, Dict, List, Set, MutableMapping, \
    Mapping

from venom import Empty
from venom import Message
from venom.exceptions import ValidationError
from venom.fields import Field, ConverterField, RepeatField, FieldDescriptor
from venom.message import field_names, fields


# def partial(message: Type[Message], include: Set[str], name: str = None):
#     if len(include) == 0:
#         return Empty
#     elif set(field_names(message)).issuperset(include):
#         return message
#     else:
#         if name is None:
#             name = 'Partial{}'.format(message.__meta__.name)
#
#         return message_factory(name, {name: field for name, field in fields(message) if name in include})


class Protocol(metaclass=ABCMeta):
    mime: str = None
    name: str = None

    def __new__(cls, fmt: Type[Message], field_names: Set[str] = None):
        if field_names is None:
            try:
                return fmt.__meta__.protocols[cls.name]
            except KeyError:
                instance = super(Protocol, cls).__new__(cls)
                instance.__init__(fmt)
                return instance
        # elif len(field_names) == 0:
        #     return Protocol.__new__(cls, Empty)
        else:
            instance = super(Protocol, cls).__new__(cls)
            instance.__init__(fmt, field_names)
            return instance

    def __init__(self, fmt: Type[Message], field_names_: Set[str] = None):
        if field_names_ is None:
            field_names_ = field_names(fmt)
            fmt.__meta__.protocols[self.name] = self
        self._format = fmt
        self._fields = [field for field in fields(fmt) if field.name in field_names_]

    @classmethod
    def _get_protocol(cls, fmt: Type[Message]):
        try:
            return fmt.__meta__.protocols[cls.name]
        except KeyError:
            return cls(fmt)

    @abstractmethod
    def pack(self, message: Message) -> bytes:
        pass

    @abstractmethod
    def unpack(self, buffer: bytes) -> Message:
        pass


try:
    import ujson as json
except ImportError:
    import json

JSONPrimitive = Union[str, int, float, bool]

JSONValue = Union[JSONPrimitive, Dict[str, JSONPrimitive], List[JSONPrimitive]]


class DictProtocol(Protocol, metaclass=ABCMeta):
    @abstractmethod
    def encode(self, message: Message):
        pass

    @abstractmethod
    def decode(self, instance: Any, message: Message = None) -> Message:
        pass


class JSON(DictProtocol):
    mime = 'application/json'
    name = 'json'

    def __init__(self, fmt: Type[Message], field_names_: Set[str] = None):
        super().__init__(fmt, field_names_)
        # TODO camelCase conversion
        self.field_encoders = {field.name: self._field_encoder(field) for field in self._fields}
        self.field_decoders = {field.name: self._field_decoder(field) for field in self._fields}

    T = TypeVar('T')

    @staticmethod
    def _cast(type_: Type[T], value: Any) -> T:
        # TODO JSON type names, i.e. object instead of dict, integer instead of int etc.
        if not isinstance(value, type_):
            raise ValidationError(f"{repr(value)} is not of type '{type_.__name__}'")
        return value

    @staticmethod
    def _cast_number(value: Any):
        if type(value) not in (int, float):
            raise ValidationError(f"{value} is not a number")
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

    def encode(self, message: Message):
        obj = {}
        for name, encode in self.field_encoders.items():
            try:
                obj[name] = encode(message[name])
            except KeyError:
                pass
        return obj

    def decode(self, instance: Any, message: Message = None) -> Message:
        if not isinstance(instance, Mapping):
            raise ValidationError(f"{repr(instance)} is not of type 'object'")

        if message is None:
            message = self._format()

        for name, decode in self.field_decoders.items():
            if name in instance:
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

    def unpack(self, buffer: bytes):
        # Allow empty string when message is empty
        if len(buffer) == 0 and not self._fields:
            return self._format()

        try:
            return self.decode(json.loads(buffer.decode('utf-8')))
        except (ValueError, JSONDecodeError) as e:
            raise ValidationError(f"Invalid JSON: {str(e)}")


class URIString(JSON):

    def _field_decoder(self, field: FieldDescriptor) -> Callable[[JSONValue], Any]:
        if isinstance(field, RepeatField):
            raise NotImplementedError(f'Unable to decode {field} from URI string')

        if not isinstance(field, Field):
            raise NotImplementedError()

        if issubclass(field.type, Message):
            raise NotImplementedError(f'Unable to decode {field} from URI string')

        if field.type is str:
            return lambda s: s

        if field.type is bytes:
            # TODO catch TypeError
            return lambda b: b64decode(b)

        return partial(self._cast, field.type)

    def _field_encoder(self, field: FieldDescriptor) -> Callable[[Any], JSONValue]:
        if isinstance(field, RepeatField):
            raise NotImplementedError(f'Unable to decode {field} from URI string')

        if not isinstance(field, Field):
            raise NotImplementedError()

        if issubclass(field.type, Message):
            raise NotImplementedError(f'Unable to decode {field} from URI string')

        if field.type is bytes:
            return lambda b: b64encode(b)

        return lambda x: str(x)

    @staticmethod
    def _cast(type_: type, value: Any):
        # TODO JSON/wire-format specific type names, i.e. object instead of dict, integer instead of int etc.
        try:
            return type_(value)
        except ValueError:
            raise ValidationError(f"{repr(value)} is not formatted as a '{type_.__name__}'")
