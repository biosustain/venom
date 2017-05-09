from unittest import TestCase

from venom import Message
from venom.protocol import URIString


class URIStringProtocolTestCase(TestCase):
    def test_encode_snake_case(self):
        class Pet(Message):
            pet_id: int

        protocol = URIString(Pet)
        self.assertEqual(protocol.encode(Pet(1)), {'petId': '1'})
        self.assertEqual(protocol.decode({'petId': '42'}), Pet(42))
        self.assertEqual(protocol.decode({}), Pet())
