from abc import ABCMeta, abstractmethod
from typing import Any
from typing import Type

from venom.message import Message


class Converter(metaclass=ABCMeta):
    wire = None  # type: Type[Message]
    python = None  # type: type

    @abstractmethod
    def convert(self, message: Message) -> Any:
        pass

    @abstractmethod
    def format(self, value: Any) -> Message:
        pass

    def __repr__(self):
        return '<converter {}[{}, {}]>'.format(self.__class__.__name__, self.python.__name__, self.wire.__name__)