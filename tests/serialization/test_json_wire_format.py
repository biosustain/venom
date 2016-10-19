from unittest import TestCase

from venom import Message
from venom.common import StringValue, IntegerValue, BoolValue, NumberValue
from venom.exceptions import ValidationError
from venom.fields import String, Number, Field, Repeat
from venom.serialization import JSON


class Foo(Message):
    string = String()
    parent = Field('tests.serialization.test_json_wire_format.Foo')
    string_value = Field(StringValue)


class JSONWireFormatTestCase(TestCase):
    def test_encode_message(self):
        class Pet(Message):
            sound = String()

        wire_format = JSON(Pet)
        self.assertEqual(wire_format.encode(Pet('hiss!')), {'sound': 'hiss!'})
        self.assertEqual(wire_format.decode({'sound': 'meow'}), Pet('meow'))
        self.assertEqual(wire_format.decode({}), Pet())

        with self.assertRaises(ValidationError) as e:
            wire_format.decode('bad')

        self.assertEqual(e.exception.message, "'bad' is not of type 'dict'")
        self.assertEqual(e.exception.path, [])

    def test_encode_message_field_attribute(self):
        class Pet(Message):
            size = Number(attribute='weight')

        wire_format = JSON(Pet)

        pet = Pet()
        pet.size = 2.5
        self.assertEqual(wire_format.encode(pet), {'weight': 2.5})
        self.assertEqual(wire_format.decode({'weight': 2.5}), Pet(2.5))

    def test_encode_repeat_field(self):
        class Pet(Message):
            sounds = Repeat(String())

        wire_format = JSON(Pet)
        self.assertEqual(wire_format.encode(Pet(['hiss!', 'slither'])), {'sounds': ['hiss!', 'slither']})
        self.assertEqual(wire_format.decode({'sounds': ['meow', 'purr']}), Pet(['meow', 'purr']))
        self.assertEqual(wire_format.decode({}), Pet())
        self.assertEqual(wire_format.encode(Pet()), {})

        with self.assertRaises(ValidationError) as e:
            wire_format.decode({'sounds': 'meow, purr'})

        self.assertEqual(e.exception.message, "'meow, purr' is not of type 'list'")
        self.assertEqual(e.exception.path, ['sounds'])

    def test_validation_field_string(self):
        class Foo(Message):
            string = String()

        wire_format = JSON(Foo)
        with self.assertRaises(ValidationError) as e:
            wire_format.decode({'string': None})

        self.assertEqual(e.exception.message, "None is not of type 'str'")
        self.assertEqual(e.exception.path, ['string'])

    def test_validation_path(self):
        wire_format = JSON(Foo)

        with self.assertRaises(ValidationError) as e:
            wire_format.decode({'string': 42})

        self.assertEqual(e.exception.message, "42 is not of type 'str'")
        self.assertEqual(e.exception.path, ['string'])

        # FIXME With custom encoding/decoding for values this won't happen.
        with self.assertRaises(ValidationError) as e:
            wire_format.decode({'string_value': {'value': None}})

        self.assertEqual(e.exception.message, "{'value': None} is not of type 'str'")
        self.assertEqual(e.exception.path, ['string_value'])

        with self.assertRaises(ValidationError) as e:
            wire_format.decode({'parent': {'string_value': 42}})

        self.assertEqual(e.exception.message, "42 is not of type 'str'")
        self.assertEqual(e.exception.path, ['parent', 'string_value'])

    def test_unpack_invalid_json(self):
        class Pet(Message):
            sound = String()

        wire_format = JSON(Pet)

        with self.assertRaises(ValidationError) as e:
            wire_format.unpack(b'')

        self.assertEqual(e.exception.message, "Invalid JSON: Expected object or value")
        self.assertEqual(e.exception.path, [])

        with self.assertRaises(ValidationError) as e:
            wire_format.unpack(b'fs"ad')

    def test_pack(self):
        class Pet(Message):
            sound = String()

        wire_format = JSON(Pet)
        self.assertEqual(wire_format.pack(Pet()), b'{}')
        self.assertEqual(wire_format.pack(Pet('hiss!')), b'{"sound":"hiss!"}')

    def test_string_value(self):
        wire_format = JSON(StringValue)

        self.assertEqual(wire_format.encode(StringValue('hiss!')), 'hiss!')
        self.assertEqual(wire_format.decode('hiss!'), StringValue('hiss!'))

        self.assertEqual(wire_format.pack(StringValue()), b'""')
        self.assertEqual(wire_format.pack(StringValue('hiss!')), b'"hiss!"')

        with self.assertRaises(ValidationError):
            wire_format.decode(42)

    def test_integer_value(self):
        wire_format = JSON(IntegerValue)

        self.assertEqual(wire_format.encode(IntegerValue(2)), 2)
        self.assertEqual(wire_format.decode(2), IntegerValue(2))

        with self.assertRaises(ValidationError):
            wire_format.decode('hiss!')

    def test_number_value(self):
        wire_format = JSON(NumberValue)

        self.assertEqual(wire_format.encode(NumberValue(2.5)), 2.5)
        self.assertEqual(wire_format.decode(2.5), NumberValue(2.5))

        with self.assertRaises(ValidationError):
            wire_format.decode('hiss!')

    def test_bool_value(self):
        wire_format = JSON(BoolValue)

        self.assertEqual(wire_format.encode(BoolValue()), False)
        self.assertEqual(wire_format.encode(BoolValue(True)), True)
        self.assertEqual(wire_format.decode(False), BoolValue(False))

        with self.assertRaises(ValidationError):
            wire_format.decode('hiss!')
