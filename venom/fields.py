from abc import ABCMeta
from importlib import import_module
from typing import Iterable, TypeVar, Generic, Any, Tuple, Union, Type

import collections

from venom.util import cached_property

T = TypeVar('T')


class FieldDescriptor(Generic[T], metaclass=ABCMeta):
    name = None  # type: Optional[str]

    def __get__(self, instance: 'venom.message.Message', owner):
        if instance is None:
            return self
        try:
            return instance[self.name]
        except KeyError:
            return self.default()

    def default(self):
        return None

    # TODO wait on https://github.com/python/mypy/issues/244
    def __set__(self, instance: 'venom.message.Message', value: T):
        instance[self.name] = value

    # TODO Use Python 3.6 __set_name__()


class Field(Generic[T], FieldDescriptor):
    def __init__(self,
                 type_: Union[T, str],
                 # TODO replace with Union[Type[T], str] see https://github.com/python/typing/issues/266
                 default: Any = None,
                 **options) -> None:
        self._type = type_
        self._default = default
        self.options = options

    def default(self):
        if self._default is None:
            return self.type()
        return self._default

    @cached_property
    def type(self) -> Type[T]:
        if isinstance(self._type, str):
            if '.' in self._type:
                module_name, class_name = self._type.rsplit('.', 1)
                module = import_module(module_name)
                return getattr(module, class_name)

            raise RuntimeError('Unable to resolve: {} in {}'.format(self._type, repr(self)))
        return self._type

    def __eq__(self, other):
        if not isinstance(other, Field):
            return False
        return self.type == other.type and self.options == other.options

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self._type)


class ConverterField(Field):
    def __init__(self,
                 type_: Type[T],
                 converter: 'venom.converter.Converter' = None,
                 **kwargs) -> None:
        super().__init__(self, converter.wire, **kwargs)
        self.python = type_
        self.converter = converter


class String(Field[str]):
    def __init__(self, **kwargs) -> None:
        super().__init__(str, **kwargs)


class Bytes(Field[bytes]):
    def __init__(self, **kwargs) -> None:
        super().__init__(bytes, **kwargs)


class Bool(Field[bool]):
    def __init__(self, **kwargs) -> None:
        super().__init__(bool, **kwargs)


class Int32(Field[int]):
    def __init__(self, **kwargs) -> None:
        super().__init__(int, **kwargs)


class Int64(Field[int]):
    def __init__(self, **kwargs) -> None:
        super().__init__(int, **kwargs)


Integer = Int64


class Float32(Field[float]):
    def __init__(self, **kwargs) -> None:
        super().__init__(float, **kwargs)


class Float64(Field[float]):
    def __init__(self, **kwargs) -> None:
        super().__init__(float, **kwargs)


Number = Float64

CT = TypeVar('CT', Field, 'MapField', 'RepeatField')


class _RepeatValueProxy(collections.MutableSequence):
    def __init__(self, message: 'venom.message.Message', name: str):
        self.message = message
        self.name = name

    @property
    def _sequence(self) -> list:
        try:
            return self.message[self.name]
        except KeyError:
            return list()

    def __len__(self):
        return len(self._sequence)

    def __getitem__(self, index):
        return self._sequence[index]

    def insert(self, index, value):
        self.message[self.name] = sequence = self._sequence
        sequence.insert(index, value)

    def __delitem__(self, index):
        self.message[self.name] = sequence = self._sequence
        del sequence[index]

    def __setitem__(self, index, value):
        self.message[self.name] = sequence = self._sequence
        sequence[index] = value

    def __iter__(self):
        return iter(self._sequence)


class RepeatField(Generic[CT], FieldDescriptor):
    def __init__(self, items: Type[CT]) -> None:
        self.items = items

    def __get__(self, instance: 'venom.message.Message', owner):
        if instance is None:
            return self
        return _RepeatValueProxy(instance, self.name)


class MapField(Generic[CT], FieldDescriptor):
    def __init__(self, values: Type[CT]) -> None:
        super().__init__()
        self.keys = String()
        self.values = values


def Repeat(items: Union[Field, MapField, RepeatField, type, str], **kwargs) -> RepeatField:
    if isinstance(items, type) and issubclass(items, Field):
        items = items()
    if not isinstance(items, (Field, MapField, RepeatField)):
        items = Field(items)
    return RepeatField(items, **kwargs)


def Map(values: Union[Field, MapField, RepeatField, type, str], **kwargs) -> MapField:
    # TODO keys argument.
    return MapField(values, **kwargs)
