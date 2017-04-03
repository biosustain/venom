from typing import Type, TypeVar

from venom import Message
from .schema import Schema

M = TypeVar('M', bound=Message)


class MessageValidator(object):
    def __init__(self, fmt: Type[M]) -> None:
        pass

    def validate(self, instance: M) -> None:
        raise NotImplementedError
