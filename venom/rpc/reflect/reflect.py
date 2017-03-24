from typing import Type, Set

from venom import Message
from venom.rpc import Method
from venom.rpc import Service


class Reflect(object):
    services: Set[Service]
    methods = Set[Method]
    messages: Set[Type[Message]]

    def __init__(self):
        self.services = set()

    def add(self, service: Type[Service]):
        self.services.add(service)
