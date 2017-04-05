from unittest import SkipTest
from unittest import TestCase

from venom import Message
from venom.common import StringValue, IntegerValue, BoolValue, NumberValue
from venom.exceptions import ValidationError
from venom.fields import String, Number, Field, Repeat
from venom.protocol import JSON


class Foo(Message):
    string = String()
    parent = Field('tests.protocol.test_json_protocol.Foo')
    string_value = Field(StringValue)


class JSONProtocolTestCase(TestCase):
    def test_encode_message(self):
        class Pet(Message):
            sound = String()

        protocol = JSON(Pet)
        self.assertEqual(protocol.encode(Pet('hiss!')), {'sound': 'hiss!'})
        self.assertEqual(protocol.decode({'sound': 'meow'}), Pet('meow'))
        self.assertEqual(protocol.decode({}), Pet())

        with self.assertRaises(ValidationError) as e:
            protocol.decode('bad')

        self.assertEqual(e.exception.description, "'bad' is not of type 'object'")
        self.assertEqual(e.exception.path, [])

    def test_encode_message_json_name(self):
        class Pet(Message):
            size = Number(json_name='$size')

        protocol = JSON(Pet)

        pet = Pet()
        pet.size = 2.5
        self.assertEqual(protocol.encode(pet), {'$size': 2.5})
        self.assertEqual(protocol.decode({'$size': 2.5}), Pet(size=2.5))
        
    def test_encode_repeat_field(self):
        class Pet(Message):
            sounds = Repeat(String())

        protocol = JSON(Pet)
        self.assertEqual(protocol.encode(Pet(['hiss!', 'slither'])), {'sounds': ['hiss!', 'slither']})
        self.assertEqual(protocol.decode({'sounds': ['meow', 'purr']}), Pet(['meow', 'purr']))
        self.assertEqual(protocol.decode({}), Pet())
        self.assertEqual(protocol.encode(Pet()), {})

        with self.assertRaises(ValidationError) as e:
            protocol.decode({'sounds': 'meow, purr'})

        self.assertEqual(e.exception.description, "'meow, purr' is not of type 'list'")
        self.assertEqual(e.exception.path, ['sounds'])

    def test_validation_field_string(self):
        class Foo(Message):
            string = String()

        protocol = JSON(Foo)
        with self.assertRaises(ValidationError) as e:
            protocol.decode({'string': None})

        self.assertEqual(e.exception.description, "None is not of type 'str'")
        self.assertEqual(e.exception.path, ['string'])

    def test_validation_path(self):
        protocol = JSON(Foo)

        with self.assertRaises(ValidationError) as e:
            protocol.decode({'string': 42})

        self.assertEqual(e.exception.description, "42 is not of type 'str'")
        self.assertEqual(e.exception.path, ['string'])

        # FIXME With custom encoding/decoding for values this won't happen.
        with self.assertRaises(ValidationError) as e:
            print(protocol.decode({'stringValue': {'value': None}}))

        self.assertEqual(e.exception.description, "{'value': None} is not of type 'str'")
        self.assertEqual(e.exception.path, ['stringValue'])

        with self.assertRaises(ValidationError) as e:
            protocol.decode({'parent': {'stringValue': 42}})

        self.assertEqual(e.exception.description, "42 is not of type 'str'")
        self.assertEqual(e.exception.path, ['parent', 'stringValue'])

    def test_unpack_invalid_json(self):
        class Pet(Message):
            sound = String()

        protocol = JSON(Pet)

        with self.assertRaises(ValidationError) as e:
            protocol.unpack(b'')

        self.assertEqual(e.exception.description, "Invalid JSON: Expected object or value")
        self.assertEqual(e.exception.path, [])

        with self.assertRaises(ValidationError) as e:
            protocol.unpack(b'fs"ad')

    def test_pack(self):
        class Pet(Message):
            sound = String()

        protocol = JSON(Pet)
        self.assertEqual(protocol.pack(Pet()), b'{}')
        self.assertEqual(protocol.pack(Pet('hiss!')), b'{"sound":"hiss!"}')

    def test_string_value(self):
        protocol = JSON(StringValue)

        self.assertEqual(protocol.encode(StringValue('hiss!')), 'hiss!')
        self.assertEqual(protocol.decode('hiss!'), StringValue('hiss!'))

        self.assertEqual(protocol.pack(StringValue()), b'""')
        self.assertEqual(protocol.pack(StringValue('hiss!')), b'"hiss!"')

        with self.assertRaises(ValidationError):
            protocol.decode(42)

    def test_integer_value(self):
        protocol = JSON(IntegerValue)

        self.assertEqual(protocol.encode(IntegerValue(2)), 2)
        self.assertEqual(protocol.decode(2), IntegerValue(2))

        with self.assertRaises(ValidationError):
            protocol.decode('hiss!')

    def test_number_value(self):
        protocol = JSON(NumberValue)

        self.assertEqual(protocol.encode(NumberValue(2.5)), 2.5)
        self.assertEqual(protocol.decode(2.5), NumberValue(2.5))

        with self.assertRaises(ValidationError):
            protocol.decode('hiss!')

    def test_bool_value(self):
        protocol = JSON(BoolValue)

        self.assertEqual(protocol.encode(BoolValue()), False)
        self.assertEqual(protocol.encode(BoolValue(True)), True)
        self.assertEqual(protocol.decode(False), BoolValue(False))

        with self.assertRaises(ValidationError):
            protocol.decode('hiss!')
