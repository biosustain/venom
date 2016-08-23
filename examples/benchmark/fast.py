from typing import Union, Any

from venom.fields import Field, MapField, RepeatField, ConverterField
from venom.message import Message
from venom.serialization import JSON


class FastValidator(object):
    def __init__(self):
        self._message_validators = {}

    def _field_validator_factory(self, field):
        if isinstance(field, RepeatField):
            validate_item = self._field_validator_factory(field.items)
            return lambda lst: isinstance(lst, list) and all(validate_item(i) for i in lst)
        elif isinstance(field, MapField):
            validate_value = self._field_validator_factory(field.values)
            return lambda dct: isinstance(dct, dict) and all(validate_value for v in dct.values())
        elif isinstance(field, ConverterField):
            return self._validator_factory(field.converter.wire)
        elif issubclass(field.type, Message):
            return self._validator_factory(field.type)

        fchecks = field.checks
        ftype = field.type
        return lambda value: isinstance(value, ftype) and all(check.check(value) for check in fchecks)

    def _validator_factory(self, cls: type(Message)):
        if cls in self._message_validators:
            return self._message_validators[cls]

        validations = []
        for field in cls.__fields__.values():
            field_validator = self._field_validator_factory(field)
            validations.append((field.attribute, field.optional, field_validator))

        validator = lambda m: isinstance(m, dict) and all((opt and attr not in m) or (attr in m and validate(m[attr]))
                                                          for attr, opt, validate in validations)

        self._message_validators[cls] = validator
        return validator

    def validate(self, instance: Any, cls: type(Message)):
        try:
            validate = self._message_validators[cls]
        except KeyError:
            validate = self._validator_factory(cls)

        if not validate(instance):
            raise ValueError()


class FastJSON(JSON):
    def __init__(self, validator_cls=FastValidator):
        super().__init__(validator_cls)
        self._encoders = {}
        self._decoders = {}

    def _field_encoder_factory(self, field: Union[Field, MapField, RepeatField]):
        if isinstance(field, RepeatField):
            encode_item = self._field_encoder_factory(field.items)
            return lambda lst: [encode_item(item) for item in lst]
        elif isinstance(field, MapField):
            encode_value = self._field_encoder_factory(field.items)
            return lambda dct: {k: encode_value(v) for k, v in dct.items()}
        elif isinstance(field, ConverterField):
            format = field.converter.format
            encode_value = self._encoder_factory(field.converter.wire)
            return lambda value: encode_value(format(value))
        elif issubclass(field.type, Message):
            return self._encoder_factory(field.type)
        return lambda value: value

    def _encoder_factory(self, cls: type(Message) = None):
        fields = []
        for name, field in cls.__fields__.items():
            fields.append((name, field.attribute, self._field_encoder_factory(field)))

        return lambda msg: {attr: encode(msg[name]) for name, attr, encode in fields if name in msg}

    def encode(self, message: Message, cls: type(Message) = None) -> Any:
        try:
            encode = self._encoders[cls]
        except KeyError:
            encode = self._encoders[cls] = self._encoder_factory(cls)

        return encode(message)

    def _field_decoder_factory(self, field: Union[Field, MapField, RepeatField]):
        if isinstance(field, RepeatField):
            decode_item = self._field_decoder_factory(field.items)
            return lambda lst: [decode_item(item) for item in lst]
        elif isinstance(field, MapField):
            decode_value = self._field_decoder_factory(field.items)
            return lambda dct: {k: decode_value(v) for k, v in dct.items()}
        elif isinstance(field, ConverterField):
            convert = field.converter.convert
            decode_value = self._decoder_factory(field.converter.wire)
            return lambda value: convert(decode_value(value))
        elif issubclass(field.type, Message):
            return self._decoder_factory(field.type)
        # TODO float/int.
        return lambda value: value

    def _decoder_factory(self, cls: type(Message) = None):
        fields = []
        for name, field in cls.__fields__.items():
            fields.append((name, field.attribute, self._field_encoder_factory(field)))

        return lambda dct: cls(**{name: encode(dct[attr]) for name, attr, encode in fields if name in dct})

    def _decode(self, message: Message, cls: type(Message) = None) -> Any:
        try:
            decode = self._decoders[cls]
        except KeyError:
            decode = self._decoders[cls] = self._decoder_factory(cls)

        return decode(message)


import msgpack


class FastMsgPack(FastJSON):
    mime = 'application/msgpack'

    def pack(self, fmt: type(Message), message: Message) -> bytes:
        return msgpack.packb(self.encode(message, cls=fmt), use_bin_type=True)

    def unpack(self, fmt: type(Message), value: bytes):
        # TODO catch JSONDecodeError
        return self.decode(msgpack.unpackb(value, encoding='utf-8'), cls=fmt)
