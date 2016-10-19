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
