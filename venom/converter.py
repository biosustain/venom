from abc import ABCMeta, abstractmethod
from typing import Any, Union, Generic, TypeVar
from typing import Type

from venom.message import Message

T = TypeVar('T', bool, int, float, str, bytes, 'venom.message.Message')

P = TypeVar('P')


class Converter(Generic[T, P], metaclass=ABCMeta):
    wire: Type[T]
    python: Type[P]

    @abstractmethod
    def convert(self, value: T) -> P:
        pass

    @abstractmethod
    def format(self, value: P) -> T:
        pass

    def __repr__(self):
        return '<converter {}[{}, {}]>'.format(self.__class__.__name__, self.python.__name__, self.wire.__name__)