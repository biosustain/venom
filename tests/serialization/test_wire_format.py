from unittest import TestCase

from venom import Message
from venom.fields import String
from venom.serialization import WireFormat


class WireFormatTestCase(TestCase):

    def test_cache(self):
        class FooWireFormat(WireFormat):
            def pack(self, message: Message):
                return b''

            def unpack(self, buffer: bytes) -> Message:
                return self._format()

        class Pet(Message):
            sound = String()

        wire_format = FooWireFormat(Pet)
        self.assertIs(Pet.__meta__.wire_formats[FooWireFormat], wire_format)


