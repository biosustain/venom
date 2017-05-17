from typing import Type, Set

from venom import Message
from venom.fields import FieldDescriptor
from venom.message import fields
from venom.rpc import Service
from venom.rpc.method import Method


class Reflect(object):
    services: Set[Service]
    methods: Set[Type[Method]]
    messages: Set[Type[Message]]

    def __init__(self, title='', version=''):
        self.title = title
        self.version = version
        self.services = set()
        self.methods = set()
        self.messages = set()

    def _add_field(self, field: FieldDescriptor):
        if issubclass(field.type, Message):
            self._add_message(field.type)

    def _add_message(self, message: Message):
        if message not in self.messages:
            self.messages.add(message)
            for field in fields(message):
                self._add_field(field)

    def _add_method(self, method: Method):
        self._add_message(method.request)
        self._add_message(method.response)
        self.methods.add(method)

    def add(self, service: Service):
        for method in service.__methods__.values():
            self._add_method(method)
        self.services.add(service)
