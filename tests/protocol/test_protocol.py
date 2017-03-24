from unittest import TestCase

from venom import Message
from venom.fields import String
from venom.protocol import Protocol


class ProtocolTestCase(TestCase):
    def test_cache(self):
        class FooProtocol(Protocol):
            name = 'foo'

            def pack(self, message: Message):
                return b''

            def unpack(self, buffer: bytes) -> Message:
                return self._format()

        class Pet(Message):
            sound = String()

        protocol = FooProtocol(Pet)
        self.assertIs(Pet.__meta__.protocols['foo'], protocol)
