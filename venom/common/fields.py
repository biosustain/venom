from typing import Any

import datetime

from venom.common import DateConverter, DateTimeConverter
from venom.fields import ConverterField


class Date(ConverterField):
    def __init__(self, **kwargs) -> None:
        super().__init__(datetime.date, converter=DateConverter(), **kwargs)


class DateTime(ConverterField):
    def __init__(self, **kwargs) -> None:
        super().__init__(datetime.datetime, converter=DateTimeConverter(), **kwargs)
