import calendar
import json
from abc import abstractmethod, ABC, ABCMeta
from base64 import b64encode, b64decode

import datetime
from functools import partial

import aniso8601 as aniso8601
from typing import Union, ClassVar, Dict, Type, Tuple, Any, TypeVar, Callable, Mapping, List

from venom import Message
from venom.common import FieldMask, Timestamp, StringValue, BytesValue, IntegerValue, NumberValue, BoolValue, JSONValue
from venom.exceptions import ValidationError
from venom.fields import FieldDescriptor


_PrimitiveValue = Union[str, int, float, bool, bytes]
_Value = Union[_PrimitiveValue, Dict[str, '_Value'], List['_Value']]


class MessageTranscoder(ABC):
    _instance_cache: ClassVar[Dict[Tuple[Type['venom.protocol.Protocol'], Type[Message]], 'MessageTranscoder']] = {}
    _defaults: ClassVar[Dict[Type[Message], Type['MessageTranscoder']]] = {}

    def __init__(self, protocol: Type['venom.protocol.Protocol'], message: Type[Message], default: bool = True):
        if default:
            MessageTranscoder._instance_cache[(protocol, message)] = self
        self.protocol = protocol
        self.message = message

    @classmethod
    def set_protocol_default(cls, protocol: Type['venom.protocol.Protocol'], message: Type[Message]):
        MessageTranscoder._defaults[(protocol, message)] = cls

    @classmethod
    def get(cls, protocol: Type['venom.protocol.Protocol'], message: Type[Message]) -> Type['MessageTranscoder']:
        try:
            return cls._defaults[(protocol, message)]
        except KeyError:
            return cls

    @classmethod
    def get_instance(cls, protocol: Type['venom.protocol.Protocol'], message: Type[Message]) -> 'MessageTranscoder':
        try:
            return MessageTranscoder._instance_cache[(protocol, message)]
        except KeyError:
            pass

        return cls.get(protocol, message)(protocol, message)

    @abstractmethod
    def encode(self, message: Message) -> _Value:
        pass

    @abstractmethod
    def decode(self, instance: _Value, message: Message = None) -> Message:
        pass


_T = TypeVar('_T')


def _cast_value(as_type: Type[_T], value: Any) -> _T:
    # TODO JSONProtocol type names, i.e. object instead of dict, integer instead of int etc.
    if not isinstance(value, as_type):
        raise ValidationError(f"{repr(value)} is not of type '{as_type.__name__}'")
    return value


def _cast_value_as_number(value: Any):
    if type(value) not in (int, float):
        raise ValidationError(f"{value} is not a number")
    return float(value)


# TODO simplify and move logic to JSONProtocol protocol.
class DictMessageTranscoder(MessageTranscoder):
    __slots__ = ('field_encoders', 'field_decoders')

    def __init__(self,
                 protocol: 'Type[venom.protocol.Protocol]',
                 message: Type[Message],
                 field_mask: FieldMask = None):

        super().__init__(protocol, message, default=field_mask is None)

        self.field_encoders = {
            (field.name, field.json_name): self.field_encoder_factory(field)
            for field in message.__fields__.values()
            if not field_mask or field_mask.match_path(field.name)}

        self.field_decoders = {
            (field.name, field.json_name): self.field_decoder_factory(field)
            for field in message.__fields__.values()
            if not field_mask or field_mask.match_path(field.name)}

    def encode(self, message: Message) -> Dict[str, _Value]:
        obj = {}
        for (name, json_name), encode in self.field_encoders.items():
            try:
                value = message[name]
                if value is not None:
                    obj[json_name] = encode(value)
            except KeyError:
                pass
        return obj

    def decode(self, instance: Any, message: Message = None) -> Message:
        if not isinstance(instance, Mapping):
            raise ValidationError(f"{repr(instance)} is not of type 'object'")

        if message is None:
            message = self.message()

        for (name, json_name), decode in self.field_decoders.items():
            if json_name in instance:
                try:
                    message[name] = decode(instance[json_name])
                except ValidationError as e:
                    e.path.insert(0, json_name)
                    raise e
        return message

    def field_encoder_factory(self, field: FieldDescriptor) -> Callable[[Any], _Value]:
        if issubclass(field.type, Message):
            field_coder = self.get_instance(self.protocol, field.type)
            encode_value = lambda msg: field_coder.encode(msg)
        elif field.type is bytes:
            encode_value = lambda b: b64encode(b)
        else:
            # assume all is JSONProtocol from here
            encode_value = lambda value: value

        if field.repeated:
            if field.key_type:
                return lambda dct: {k: encode_value(v) for k, v in dct.items()}
            return lambda lst: [encode_value(v) for v in lst]
        return encode_value

    def field_decoder_factory(self, field: FieldDescriptor) -> Callable[[_Value], Any]:
        if issubclass(field.type, Message):
            field_coder = self.get_instance(self.protocol, field.type)
            decode_value = lambda msg: field_coder.decode(msg)
        elif field.type is float:
            # an integer (int) in JSONProtocol is also a number (float), so we convert here if necessary:
            decode_value = _cast_value_as_number
        elif field.type is bytes:
            # TODO catch TypeError
            decode_value = lambda b: b64decode(b)
        else:
            # assume all is JSONProtocol from here
            decode_value = partial(_cast_value, field.type)

        if field.repeated:
            if field.key_type:
                return lambda dct: {k: decode_value(v) for k, v in _cast_value(dict, dct).items()}
            return lambda lst: [decode_value(item) for item in _cast_value(list, lst)]
        return decode_value


def _cast_value_from_string(as_type: type, value: Any):
    # TODO JSONProtocol/wire-format specific type names, i.e. object instead of dict, integer instead of int etc.
    try:
        return as_type(value)
    except ValueError:
        raise ValidationError(f"{repr(value)} is not formatted as a '{as_type.__name__}'")


class URIStringDictMessageTranscoder(DictMessageTranscoder):
    def field_decoder_factory(self, field: FieldDescriptor) -> Callable[[_Value], Any]:
        from venom.protocol import JSONProtocol

        if field.repeated:
            protocol = JSONProtocol(field.type)

            def _decode_value(msg):
                return protocol.unpacks(msg.encode('utf-8'))

            if field.key_type:
                return lambda dct: {k: _decode_value(v) for k, v in _cast_value(dict, dct).items()}
            return lambda lst: [_decode_value(item) for item in _cast_value(list, lst)]

        if issubclass(field.type, Message):
            protocol = JSONProtocol(field.type)

            def _decode_value(msg):
                return protocol.unpacks(msg.encode('utf-8'))

            return _decode_value

        if field.type is str:
            return lambda s: s

        if field.type is bytes:
            # TODO catch TypeError
            return lambda b: b64decode(b)

        return partial(_cast_value_from_string, field.type)

    def field_encoder_factory(self, field: FieldDescriptor) -> Callable[[Any], _Value]:
        from venom.protocol import JSONProtocol

        if field.repeated:
            protocol = JSONProtocol(field.type)

            if field.key_type:
                return lambda dct: {k: protocol.packs(v) for k, v in dct.items()}
            return lambda lst: [protocol.packs(v) for v in lst]

        if issubclass(field.type, Message):
            protocol = JSONProtocol(field.type)
            return protocol.packs

        if field.type is bytes:
            return lambda b: b64encode(b)

        return lambda x: str(x)


class JSONTranscoder(MessageTranscoder):
    def encode(self, message: JSONValue):
        return json.loads(message.value)

    def decode(self, instance: Any, message: Message = None) -> Message:
        return self.message(instance)


class JSONValueTranscoder(MessageTranscoder):
    def encode(self, message: Union[StringValue, IntegerValue, NumberValue, BoolValue, BytesValue]):
        return message.value

    def decode(self, instance: Any, message: Message = None) -> Message:
        value = _cast_value(self.message.value.type, instance)
        return self.message(value)


class JSONTimestampTranscoder(MessageTranscoder):
    def encode(self, timestamp: Timestamp):
        dt = datetime.datetime.utcfromtimestamp(timestamp.seconds + timestamp.nanos / 10 ** 9)
        return dt.isoformat()

    def decode(self, instance: Any, message: Message = None) -> Message:
        try:
            # FIXME enforce UTC
            dt = aniso8601.parse_datetime(_cast_value(str, instance))
        except ValueError:
            raise ValidationError(f"{repr(instance)} is not a 'date' or 'date-time'")
        unix = calendar.timegm(dt.utctimetuple())
        seconds = int(unix)
        nanos = int((unix - seconds) * 10 ** 9)
        return Timestamp(seconds, nanos)


class JSONFieldMaskTranscoder(MessageTranscoder):
    def encode(self, message: FieldMask):
        return ','.join(message.paths)

    def decode(self, instance: Any, message: Message = None) -> Message:
        paths = _cast_value(str, instance)
        return self.message(paths.split(','))
