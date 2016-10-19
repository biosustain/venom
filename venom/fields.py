from abc import ABCMeta
from importlib import import_module
from typing import Iterable, TypeVar, Generic, Any, Tuple, Union

import collections

from venom.util import cached_property


T = TypeVar('T')


class FieldDescriptor(Generic[T], metaclass=ABCMeta):
    attribute = None  # type: Optional[str]

    def __get__(self, instance: 'venom.message.Message', owner):
        if instance is None:
            return self
        try:
            return instance[self.attribute]
        except KeyError:
            return self.default()

    def default(self):
        return None

    # https://github.com/python/mypy/issues/244
    def __set__(self, instance: 'venom.message.Message', value: T):
        instance[self.attribute] = value


class Field(Generic[T], FieldDescriptor):
    def __init__(self,
                 type_: Union[T, str],  # Type[T]
                 attribute: str = None,
                 default: Any = None,
                 **options) -> None:
        self._type = type_
        self._default = default
        self.attribute = attribute
        self.options = options

    def default(self):
        if self._default is None:
            return self.type()
        return self._default

    @cached_property
    def type(self) -> T:
        if isinstance(self._type, str):
            if '.' in self._type:
                module_name, class_name = self._type.rsplit('.', 1)
                module = import_module(module_name)
                return getattr(module, class_name)

            raise RuntimeError('Unable to resolve: {} in {}'.format(self._type, repr(self)))
        return self._type

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.type == other.type and \
               self.attribute == other.attribute and \
               self.options == other.options

    def __repr__(self):
        return '{}({}, attribute={})'.format(self.__class__.__name__, self._type, repr(self.attribute))


class ConverterField(Field):
    def __init__(self,
                 type_: T,  # Type[T]
                 converter: 'venom.converter.Converter' = None,
                 **kwargs) -> None:
        super().__init__(self, converter.wire, **kwargs)
        self.python = type_
        self.converter = converter


def String(**kwargs) -> Field[str]:
    return Field(str, **kwargs)


def Bool(**kwargs) -> Field[bool]:
    return Field(bool, **kwargs)


def Int32(**kwargs) -> Field[int]:
    return Field(int, **kwargs)


def Int64(**kwargs) -> Field[int]:
    return Field(int, **kwargs)


Integer = Int64


def Float32(**kwargs) -> Field[float]:
    return Field(float, **kwargs)


def Float64(**kwargs) -> Field[float]:
    return Field(float, **kwargs)


Number = Float64


CT = TypeVar('CT', Field, 'MapField', 'RepeatField')


class _RepeatValueProxy(collections.MutableSequence):
    def __init__(self, message: 'venom.message.Message', attribute: str):
        self.message = message
        self.attribute = attribute

    @property
    def _sequence(self) -> list:
        try:
            return self.message[self.attribute]
        except KeyError:
            return list()

    def __len__(self):
        return len(self._sequence)

    def __getitem__(self, index):
        return self._sequence[index]

    def insert(self, index, value):
        self.message[self.attribute] = sequence = self._sequence
        sequence.insert(index, value)

    def __delitem__(self, index):
        self.message[self.attribute] = sequence = self._sequence
        del sequence[index]

    def __setitem__(self, index, value):
        self.message[self.attribute] = sequence = self._sequence
        sequence[index] = value

    def __iter__(self):
        return iter(self._sequence)


class RepeatField(Generic[CT], FieldDescriptor):
    def __init__(self,
                 items: CT,
                 attribute: str = None) -> None:
        self.attribute = attribute
        self.items = items

    def __get__(self, instance: 'venom.message.Message', owner):
        if instance is None:
            return self
        return _RepeatValueProxy(instance, self.attribute)


class MapField(Generic[CT], FieldDescriptor):
    def __init__(self,
                 values: CT,
                 attribute: str = None) -> None:
        super().__init__(attribute=attribute)
        self.keys = String()
        self.values = values


def Repeat(items: Union[Field, MapField, RepeatField, type], **kwargs) -> RepeatField:
    if not isinstance(items, (Field, MapField, RepeatField)):
        items = Field(items)
    return RepeatField(items, **kwargs)


def Map(values: Union[Field, MapField, RepeatField, type], **kwargs) -> MapField:
    # TODO keys argument.
    return MapField(values, **kwargs)
