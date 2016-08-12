from typing import Union

import datetime

from venom.common.messages import Date
from venom.converter import Converter

BuiltInType = Union[type(None), bool, int, str, float, 'venom.message.Message']


class DateConverter(Converter):
    wire = Date
    python = datetime.date

    def convert(self, message: Date) -> datetime.date:
        return datetime.datetime.strptime(message.value, '%Y-%m-%d').date()

    def format(self, value: datetime.date) -> str:
        return Date(value=value.strftime('%Y-%m-%d'))
