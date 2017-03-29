import enum

from typing import Iterable, Any, Tuple

from venom.fields import String, Int32, Int64, Bool, Float32, Float64, Repeat, Bytes, Field, Map
from venom.message import Message, one_of


class StringValue(Message):
    value = String()

    class Meta:
        proto_package = 'google.protobuf'


class BytesValue(Message):
    value = Bytes()

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


class NullValue(enum.Enum):
    NULL_VALUE = None


class Struct(Message):
    fields = Map('venom.common.messages.Value')


class ListValue(Message):
    values = Repeat('venom.common.messages.Value')


class Value(Message):
    # null_value = Field(NullValue)
    number_value = Field(NumberValue)
    string_value = Field(StringValue)
    bool_value = Field(BoolValue)
    struct_value = Field(Struct)
    list_value = Field(ListValue)

    value = one_of(  # null_value,
                   number_value,
                   string_value,
                   bool_value,
                   struct_value,
                   list_value)


from venom.protocol import JSON as _JSON


class _JSONValue(_JSON):
    def encode(self, message: Message):
        return message.value

    def decode(self, instance: Any, skip: Iterable[str] = ()) -> Message:
        value = self._cast(self._format.value.type, instance)
        return self._format(value)


StringValue.__meta__.protocols['json'] = _JSONValue(StringValue)
IntegerValue.__meta__.protocols['json'] = _JSONValue(IntegerValue)
NumberValue.__meta__.protocols['json'] = _JSONValue(NumberValue)
BoolValue.__meta__.protocols['json'] = _JSONValue(BoolValue)


class FieldMask(Message):
    paths = Repeat(String())

    class Meta:
        proto_package = 'google.protobuf'

    # TODO needs tests
    def match_path(self, *path: Tuple[str]) -> bool:
        for level in range(len(path)):
            match_path = '.'.join(path[:level + 1])
            for path_ in self.paths:
                if match_path in path_:
                    return True
        return False


class _JSONFieldMask(_JSON):
    def encode(self, message: FieldMask):
        return ','.join(message.paths)

    def decode(self, instance: Any, skip: Iterable[str] = ()) -> Message:
        paths = self._cast(str, instance)
        return self._format(paths.split(','))


FieldMask.__meta__.protocols['json'] = _JSONFieldMask(FieldMask)


class Timestamp(Message):
    seconds = Int64()
    nanos = Int32()

    class Meta:
        proto_package = 'google.protobuf'


clas