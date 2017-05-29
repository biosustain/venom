from typing import List

from venom import Message
from venom.common import Value
from venom.common.fields import NullableField


class Schema(Message):
    minimum = NullableField(float)
    maximum = NullableField(float)

    exclusive_minimum: bool
    exclusive_maximum: bool

    min_length: int
    max_length = NullableField(int)

    format: str
    pattern: str

    min_items: int
    max_items = NullableField(int)
    unique_items: bool

    min_properties: int
    max_properties = NullableField(int)

    enum: List[Value]

    multiple_of: float
