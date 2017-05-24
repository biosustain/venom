import calendar
import enum
import json

import datetime
from typing import Iterable, Any, Tuple

from venom.exceptions import ValidationError
from venom.fields import String, Int32, Int64, Bool, Float32, Float64, repeated, Bytes, Field, MapField, Repeat
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
    fields = MapField('venom.common.messages.Value')


class ListValue(Message):
    values = repeated('venom.common.messages.Value')


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


class JSONValue(Message):
    value = String()

    def __init__(self, value):
        super().__init__(json.dumps(value))


class FieldMask(Message):
    paths: Repeat[str]

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


class Timestamp(Message):
    seconds = Int64()
    nanos = Int32()

    class Meta:
        proto_package = 'google.protobuf'

