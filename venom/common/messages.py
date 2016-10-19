from typing import Iterable, Any

from venom.fields import String, Int32, Int64, Bool, Float32, Float64
from venom.message import Message


class StringValue(Message):
    value = String()

    class Meta:
        proto_package = 'google.protobuf'


class BoolValue(Message):
    value = Bool()

    class Meta:
        proto_package = 'google.protobuf'


class Int32Value(Message):
    value = Int32()

    class Meta:
        proto_package = 'google.protobuf'


class Int64Value(Message):
    value = Int64()

    class Meta:
        proto_package = 'google.protobuf'


IntegerValue = Int64Value


class Float32Value(Message):
    value = Float32()

    class Meta:
        proto_package = 'google.protobuf'


class Float64Value(Message):
    value = Float64()

    class Meta:
        proto_package = 'google.protobuf'


NumberValue = Float64Value

# class Value(Message):
#     value = one_of(
#         number_value=Number(),
#         string_value=String(),
#         # bool_value=Boolean()
#         # TODO
#     )

from venom.serialization import JSON as _JSON


class _JSONValue(_JSON):
    mime = 'application/json'

    def encode(self, message: Message):
        return message.value

    def decode(self, instance: Any, skip: Iterable[str] = ()) -> Message:
        value = self._cast(self._format.value.type, instance)
        return self._format(value)


StringValue.__meta__.wire_formats[_JSON] = _JSONValue(StringValue)
IntegerValue.__meta__.wire_formats[_JSON] = _JSONValue(IntegerValue)
NumberValue.__meta__.wire_formats[_JSON] = _JSONValue(NumberValue)
BoolValue.__meta__.wire_formats[_JSON] = _JSONValue(BoolValue)
