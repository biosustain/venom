from abc import ABCMeta
from typing import Iterable, TypeVar, Generic, Any, Tuple, Union

from venom.checks import Check, FormatCheck, StringCheck, Choice, PatternCheck, MaxLength, GreaterThanEqual, \
    LessThanEqual, RepeatCheck, UniqueItems, MapCheck

from venom.types import int32, int64

T = TypeVar('T')


class FieldDescriptor(Generic[T], metaclass=ABCMeta):
    attribute = None  # type: Optional[str]

    def __get__(self, instance: 'venom.message.Message', owner):
        if instance is None:
            return self
        try:
            return instance[self.attribute]
        except KeyError:
            if self.optional:
                value = instance[self.attribute] = self.default
                return value
            raise AttributeError

    # https://github.com/python/mypy/issues/244
    def __set__(self, instance: 'venom.message.Message', value: T):
        instance[self.attribute] = value



class Field(FieldDescriptor):
    def __init__(self,
                 type_: T,  # Type[T]
                 *checks: Tuple[Check],
                 attribute: str = None,
                 optional: bool = True,
                 default: Any = None,
                 **options) -> None:
        self.type = type_
        self.checks = checks
        self.attribute = attribute
        self.optional = optional
        self.default = default
        self.options = options


class ConverterField(Field):
    def __init__(self,
                 type_: T,  # Type[T]
                 *checks: Tuple[Check],
                 converter: 'venom.converter.Converter' = None,
                 **kwargs) -> None:
        super().__init__(self, converter.wire, *checks, **kwargs)
        self.python = type_
        self.converter = converter


def String(*checks: StringCheck,
           choices: Iterable[str] = None,
           max_length: int = None,
           format: str = None,
           pattern: str = None,
           **kwargs) -> Field[str]:
    if choices is not None:
        checks += Choice(choices),
    if format is not None:
        checks += FormatCheck(format),
    if pattern is not None:
        checks += PatternCheck(pattern),
    if max_length is not None:
        checks += MaxLength(max_length),

    return Field(str, *checks, **kwargs)


def Boolean(**kwargs) -> Field[bool]:
    return Field(bool, **kwargs)


Bool = Boolean


def URI(*checks: StringCheck, **kwargs) -> Field[str]:
    return String(*checks, format='uri', **kwargs)


def Email(*checks: StringCheck, **kwargs) -> Field[str]:
    return String(*checks, format='email', **kwargs)


def Integer(*checks: Check,
            minimum=None,
            maximum=None,
            **kwargs) -> Field[int]:
    if minimum is not None:
        checks += GreaterThanEqual(minimum),
    if maximum is not None:
        checks += LessThanEqual(maximum),
    return Field(int, *checks, **kwargs)


def Int32(**kwargs):
    return Field(int32, FormatCheck('int32'))


def Int64(**kwargs):
    return Field(int64, FormatCheck('int64'))


def Number(*checks: Check, **kwargs) -> Field[float]:
    # TODO minimum, maximum, exclusive_minimum, exclusive_maximum.
    return Field(float, *checks, **kwargs)


CT = TypeVar('CT', Field, 'MapField', 'RepeatField')


class RepeatField(Generic[CT], FieldDescriptor):
    def __init__(self,
                 items: CT,
                 *checks: RepeatCheck,
                 attribute: str = None,
                 optional: bool = False) -> None:
        self.items = items
        # TODO need to enforce that there is only one check of a certain type
        self.repeat_container_checks = checks
        self.attribute = attribute
        self.optional = optional


class MapField(Generic[CT], FieldDescriptor):
    def __init__(self,
                 values: CT,
                 *checks: MapCheck,
                 attribute: str = None,
                 optional: bool = False) -> None:
        self.keys = String()
        self.values = values
        # TODO need to enforce that there is only one check of a certain type
        self.map_container_checks = checks
        self.attribute = attribute
        self.optional = optional


def Repeat(items: Union[Field, MapField, RepeatField, type],
           *checks: RepeatCheck,
           unique: bool = None,
           **kwargs) -> RepeatField:
    # TODO separate key checks from mapping checks here.
    if not isinstance(items, (Field, MapField, RepeatField)):
        items = Field(items)
    if unique is not None:
        checks += UniqueItems(unique=unique),
    return RepeatField(items, *checks, **kwargs)


def Map(values: Union[Field, MapField, RepeatField, type],
        *checks: MapCheck,
        **kwargs) -> MapField:
    # TODO keys argument.
    # TODO separate key checks from mapping checks here.
    if not isinstance(values, (Field, MapField, RepeatField)):
        values = Field(values)
    return MapField(values, *checks, **kwargs)