from typing import TypeVar, Generic

from venom.common.messages import Int64Value, Int32Value, StringValue, Float32Value, Float64Value, BoolValue
from venom.converter import Converter

V = TypeVar('V')
T = TypeVar('T')


class _ValueConverter(Generic[V, T], Converter):
    def convert(self, message: V) -> T:
        return message.value

    def format(self, value: T) -> V:
        return self.wire(value=value)


class StringValueConverter(_ValueConverter[StringValue, str]):
    wire = StringValue
    python = str


class BooleanValueConverter(_ValueConverter[StringValue, bool]):
    wire = BoolValue
    python = bool


class Int32ValueConverter(_ValueConverter[Int32Value, int]):
    wire = Int32Value
    python = int


class Int64ValueConverter(_ValueConverter[Int64Value, int]):
    wire = Int64Value
    python = int


IntegerValueConverter = Int64ValueConverter


class Float32ValueConverter(_ValueConverter[Float32Value, float]):
    wire = Float32Value
    python = float


class Float64ValueConverter(_ValueConverter[Float64Value, float]):
    wire = Float64Value
    python = float


NumberValueConverter = Float64ValueConverter
