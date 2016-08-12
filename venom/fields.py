from abc import ABCMeta
from typing import Iterable, TypeVar, Generic, Any

from venom.checks import Check, FormatCheck, StringCheck, Choice, PatternCheck, MaxLength, GreaterThanEqual, \
    LessThanEqual
from venom.converter import Converter
from venom.types import int32, int64


class FieldDescriptor(metaclass=ABCMeta):
    name = None  # type: Optional[str]

    def __get__(self, instance: 'venom-1.message.Message', owner):
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
    def __set__(self, instance: 'venom-1.message.Message', value: T):
        instance[self.attribute] = value


T = TypeVar('T')


class FieldType(Generic[T]):
    def __init__(self, type_: T, *checks: Check):
        self.type = type_
        self.checks = checks

        # TODO need to enforce that there is only one check of a certain type
        # TODO enforce only checks of correct type.
        # for check in checks:
        #     assert issubclass(type_, check.type)


class Field(FieldType, FieldDescriptor):
    def __init__(self,
                 type_: T,  # Type[T]
                 *checks: Check,
                 attribute: str = None,
                 optional: bool = True,
                 default: Any = None,
                 **options) -> None:
        FieldType.__init__(self, type_, *checks)
        self.attribute = attribute
        self.optional = optional
        self.default = default
        self.options = options


class ConverterField(Field):
    def __init__(self,
                 type_: T,  # Type[T]
                 *checks: Check,
                 converter: Converter = None,
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
