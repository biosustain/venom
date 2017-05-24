from typing import List
from unittest import TestCase

from venom import Message
from venom.exceptions import ValidationError
from venom.protocol import URIStringProtocol, URIStringDictMessageTranscoder


class URIStringProtocolTestCase(TestCase):
    def test_encode_snake_case(self):
        class Pet(Message):
            pet_id: int

        transcoder = URIStringDictMessageTranscoder(URIStringProtocol, Pet)
        self.assertEqual(transcoder.encode(Pet(1)), {'petId': '1'})
        self.assertEqual(transcoder.decode({'petId': '42'}), Pet(42))
        self.assertEqual(transcoder.decode({}), Pet())

    def test_decode_message(self):
        class Foo(Message):
            name: str

        class Pet(Message):
            pet_id: int
            foo: Foo

        protocol = URIStringDictMessageTranscoder(URIStringProtocol, Pet)
        self.assertEqual(protocol.decode({'petId': '42', 'foo': '{"name": "Bar"}'}), Pet(42, Foo("Bar")))

        with self.assertRaises(ValidationError):
            protocol.decode({'petId': '42', 'foo': '{123'})


    def test_decode_repeat_message(self):
        class Foo(Message):
            name: str

        class Pet(Message):
            pet_id: int
            foo: List[Foo]

        protocol = URIStringDictMessageTranscoder(URIStringProtocol, Pet)
        self.assertEqual(protocol.encode(Pet(42, [Foo("Bar")])), {'petId': '42', 'foo': ['{"name":"Bar"}']})
