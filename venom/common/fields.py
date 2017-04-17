from venom.common import DateConverter, DateTimeConverter
from venom.fields import ConverterField


class Date(ConverterField):
    def __init__(self, **kwargs) -> None:
        super().__init__(DateConverter(), **kwargs)


class DateTime(ConverterField):
    def __init__(self, **kwargs) -> None:
        super().__init__(DateTimeConverter(), **kwargs)
