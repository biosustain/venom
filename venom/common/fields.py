import datetime

from venom.common.converters import DateConverter
from venom.fields import ConverterField


def Date(**kwargs):
    return ConverterField(datetime.date, **kwargs, converter=DateConverter)


def DateTime(**kwargs):
    return ConverterField(datetime.datetime, **kwargs, converter=DateTimeConverter)
