from typing import overload, Union

from venom.common import DateConverter, DateTimeConverter, StringValueConverter, NumberValueConverter, \
    IntegerValueConverter, BoolValueConverter, BytesValueConverter
from venom.fields import ConverterField, _PT


class Date(ConverterField):
    def __init__(self, **kwargs) -> None:
        super().__init__(DateConverter(), **kwargs)


class DateTime(ConverterField):
    def __init__(self, **kwargs) -> None:
        super().__init__(DateTimeConverter(), **kwargs)


# TODO make repeatable()
class NullableField(ConverterField):
    def __init__(self,
                 type_: type,
                 **kwargs) -> None:
        try:
            converter_cls = {
                float: NumberValueConverter,
                int: IntegerValueConverter,
                str: StringValueConverter,
                bool: BoolValueConverter,
                bytes: BytesValueConverter
            }[type_]
        except KeyError:
            raise NotImplementedError
        super().__init__(converter_cls(), **kwargs)

    def __set__(self, instance: 'venom.Message', value: Union[_PT, None]) -> None:
        if value is None:
            del instance[self.name]
        else:
            instance[self.name] = self.converter.format(value)

    @overload
    def __get__(self, instance: None, owner) -> 'ConverterField[_VT, _PT]':
        pass

    @overload
    def __get__(self, instance: 'venom.Message', owner) -> Union[_PT, None]:
        pass

    def __get__(self, instance, owner):
        if instance is None:
            return self

        try:
            value = instance[self.name]
        except KeyError:
            return None

        return self.converter.resolve(value)

# TODO nullable() helper function
