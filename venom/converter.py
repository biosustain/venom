from abc import ABCMeta, abstractmethod

from typing import Generic, TypeVar, Callable
from typing import Type

from venom.message import items, field_names

T = TypeVar('_T', bool, int, float, str, bytes, 'venom.message.Message')

P = TypeVar('P')


class Converter(Generic[T, P], metaclass=ABCMeta):
    wire: Type[T]
    python: Type[P]

    @abstractmethod
    def resolve(self, value: T) -> P:
        pass

    @abstractmethod
    def format(self, value: P) -> T:
        pass

    def __repr__(self):
        return '<converter {}[{}, {}]>'.format(self.__class__.__name__, self.python.__name__, self.wire.__name__)


_M = TypeVar('M', bound='venom.Message')
_P = TypeVar('P')


class ObjectAttrMapper(Converter[_M, _P]):
    def __init__(self, message_cls: Type[_M], python_cls: Callable[[], _P] = None, **attr_converters: Converter):
        self._python_cls = python_cls
        self._message_cls = message_cls
        self._attr_converters = attr_converters

    def resolve(self, msg: _M, obj: _P = None) -> _P:
        if obj is None:
            obj = self._python_cls()

        for name, value in items(msg):
            converter = self._attr_converters.get(name)
            if converter:
                value = converter.resolve(value)
            setattr(obj, name, value)

        return obj

    def format(self, obj: _P) -> _M:
        msg = self._message_cls()
        for name in field_names(self._message_cls):
            value = getattr(obj, name, None)
            converter = self._attr_converters.get(name)
            if value is not None and converter:
                value = converter.format(value)
            msg[name] = value
        return msg

    @property
    def python(self):
        return self._python_cls

    @property
    def wire(self):
        return self._message_cls

