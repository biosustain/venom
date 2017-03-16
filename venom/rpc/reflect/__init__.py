from typing import Type, Set, NamedTuple

from venom import Message
from venom.rpc import Service
from .service import ReflectService


class MethodBinding(NamedTuple):
    venom: Type[Service]
    service: Type[Service]


class Reflect(object):
    methods = Set[MethodBinding]
    messages: Set[Type[Message]]

    def __init__(self):
        pass

    def add(self, service: Type[Service]):
        raise NotImplementedError
