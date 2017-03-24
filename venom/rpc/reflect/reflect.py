from typing import Type, Set

from venom import Message
from venom.rpc import Method
from venom.rpc import Service


class Reflect(object):
    methods = Set[Method]
    messages: Set[Type[Message]]

    def __init__(self):
        pass

    def add(self, service: Type[Service]):
        raise NotImplementedError
