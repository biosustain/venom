from abc import ABCMeta, abstractmethod
from typing import Any

from venom.message import Message


class Converter(metaclass=ABCMeta):
    wire = None  # type: type(Message)
    python = None  # type: type

    @abstractmethod
    def convert(self, message: Message) -> Any:
        pass

    @abstractmethod
    def format(self, value: Any) -> Message:
        pass
