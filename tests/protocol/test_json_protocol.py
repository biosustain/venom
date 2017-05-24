from unittest import SkipTest
from unittest import TestCase

from venom import Message
from venom.common import StringValue, IntegerValue, BoolValue, NumberValue, FieldMask, Timestamp, Repeat
from venom.exceptions import ValidationError
from venom.fields import String, Number, Field, repeated, Map, MapField
from venom.protocol import JSONProtocol


class Foo(Message):
    string: str
    # TODO support self-referential hints
    parent = Field('tests.protocol.test_json_protocol.Foo')
    string_value: StringValue


class JSONProtocolTestCase(TestCase):
    def test_encode_message(self):
        class Pet(Message):
            sound: str

        protocol = JSONProtocol(Pet)
        self.assertEqual(protocol.encode(Pet('hiss!')), {'sound': 'hiss!'})
        self.assertEqual(protocol.decode({'sound': 'meow'}), Pet('meow'))
        self.assertEqual(protocol.decode({}), Pet())

        with self.assertRaises(ValidationError) as e:
            protocol.decode('bad')

        self.assertEqual(e.exception.description, "'bad' is not of type 'object'")
        self.assertEqual(e.exception.path, [])

    def test_encode_with_field_mask(self):
        class Pet(Message):
            sound: str
            size: int

        protocol = JSONProtocol(Pet, FieldMask(['sound']))
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

        protocol = JSONProtocol(Pet)

        pet = Pet()
        pet.size = 2.5
        self.assertEqual(protocol.encode(pet), {'$size': 2.5})
        self.assertEqual(protocol.decode({'$size': 2.5}), Pet(size=2.5))
        
    def test_encode_repeat_field(self):
        class Pet(Message):
            sounds = repeated(String())

        self.assertEqual(Pet.sounds.repeated, True)

        protocol = JSONProtocol(Pet)
        self.assertEqual(protocol.encode(Pet(['hiss!', 'slither'])), {'sounds': ['hiss!', 'slither']})
        self.assertEqual(protocol.decode({'sounds': ['meow', 'purr']}), Pet(['meow', 'purr']))
        self.assertEqual(protocol.decode({}), Pet())
        self.assertEqual(protocol.encode(Pet()), {})

        with self.assertRaises(ValidationError) as e:
            protocol.decode({'sounds': 'meow, purr'})

        self.assertEqual(e.exception.description, "'meow, purr' is not of type 'list'")
        self.assertEqual(e.exception.path, ['sounds'])

    def test_encode_decode_map(self):
        class FooInner(Message):
            i = String()

        class Foo(Message):
            m = MapField(str)
            f = MapField(FooInner)

        message = Foo(m={'a': 'b'}, f={'k': FooInner(i='in')})
        protocol = JSONProtocol(Foo)
        self.assertEqual(dict(message.m), {'a': 'b'})
        self.assertEqual(dict(message.f), {'k': FooInner(i='in')})
        self.assertEqual(protocol.encode(message), {'m': {'a': 'b'}, 'f': {'k': {'i': 'in'}}})
        self.assertEqual(protocol.decode({'m': {'a': 'b'}, 'f': {'k': {'i': 'in'}}}), message)

    def test_validation_field_string(self):
        class Foo(Message):
            string = String()

        protocol = JSONProtocol(Foo)
        with self.assertRaises(ValidationError) as e:
            protocol.decode({'string': None})

        self.assertEqual(e.exception.description, "None is not of type 'str'")
        self.assertEqual(e.exception.path, ['string'])

    def test_validation_path(self):
        protocol = JSONProtocol(Foo)

        with self.assertRaises(ValidationError) as e:
            protocol.decode({'string': 42})

        self.assertEqual(e.exception.description, "42 is not of type 'str'")
        self.assertEqual(e.exception.path, ['string'])

        # FIXME With custom encoding/decoding for values this won't happen.
        with self.assertRaises(ValidationError) as e:
            protocol.decode({'stringValue': {'value': None}})

        self.assertEqual(e.exception.description, "{'value': None} is not of type 'str'")
        self.assertEqual(e.exception.path, ['stringValue'])

        with self.assertRaises(ValidationError) as e:
            protocol.decode({'parent': {'stringValue': 42}})

        self.assertEqual(e.exception.description, "42 is not of type 'str'")
        self.assertEqual(e.exception.path, ['parent', 'stringValue'])

    def test_unpack_invalid_json(self):
        class Pet(Message):
            sound = String()

        protocol = JSONProtocol(Pet)

        with self.assertRaises(ValidationError) as e:
            protocol.unpack(b'')

        self.assertEqual(e.exception.description, "Invalid JSONProtocol: Expected object or value")
        self.assertEqual(e.exception.path, [])

        with self.assertRaises(ValidationError) as e:
            protocol.unpack(b'fs"ad')

    def test_pack(self):
        class Pet(Message):
            sound = String()

        protocol = JSONProtocol(Pet)
        self.assertEqual(protocol.pack(Pet()), b'{}')
        self.assertEqual(protocol.pack(Pet('hiss!')), b'{"sound":"hiss!"}')

    def test_string_value(self):
        protocol = JSONProtocol(StringValue)

        self.assertEqual(protocol.encode(StringValue('hiss!')), 'hiss!')
        self.assertEqual(protocol.decode('hiss!'), StringValue('hiss!'))

        self.assertEqual(protocol.pack(StringValue()), b'""')
        self.assertEqual(protocol.pack(StringValue('hiss!')), b'"hiss!"')

        with self.assertRaises(ValidationError):
            protocol.decode(42)

    def test_integer_value(self):
        protocol = JSONProtocol(IntegerValue)

        self.assertEqual(protocol.encode(IntegerValue(2)), 2)
        self.assertEqual(protocol.decode(2), IntegerValue(2))

        with self.assertRaises(ValidationError):
            protocol.decode('hiss!')

    def test_number_value(self):
        protocol = JSONProtocol(NumberValue)

        self.assertEqual(protocol.encode(NumberValue(2.5)), 2.5)
        self.assertEqual(protocol.decode(2.5), NumberValue(2.5))

        with self.assertRaises(ValidationError):
            protocol.decode('hiss!')

    def test_bool_value(self):
        protocol = JSONProtocol(BoolValue)

        self.assertEqual(protocol.encode(BoolValue()), False)
        self.assertEqual(protocol.encode(BoolValue(True)), True)
        self.assertEqual(protocol.decode(False), BoolValue(False))

        with self.assertRaises(ValidationError):
            protocol.decode('hiss!')

    def test_repeat(self):
        class Pet(Message):
            sounds: Repeat[str]

        protocol = JSONProtocol(Pet)

        self.assertEqual(protocol.encode(Pet(['hiss!', '(slither)'])), {'sounds': ['hiss!', '(slither)']})
        self.assertEqual(protocol.decode({"sounds": ['hiss!']}), Pet(['hiss!']))
        self.assertEqual(protocol.decode({}), Pet())

        self.assertEqual(protocol.pack(Pet()), b'{}')
        self.assertEqual(protocol.pack(Pet([])), b'{}')
        self.assertEqual(protocol.pack(Pet(['hiss!'])), b'{"sounds":["hiss!"]}')

        self.assertEqual(protocol.unpack(b'{}'), Pet())
        self.assertEqual(protocol.unpack(b'{"sounds":["hiss!"]}'), Pet(['hiss!']))

    def test_field_mask(self):
        protocol = JSONProtocol(FieldMask)

        self.assertEqual(protocol.encode(FieldMask(['a', 'b'])), 'a,b')
        self.assertEqual(protocol.decode('a,b'), FieldMask(['a', 'b']))

    def test_timestamp(self):
        protocol = JSONProtocol(Timestamp)

        self.assertEqual(protocol.decode('2017-10-10T12:34:56Z'), Timestamp(1507638896, 0))
        self.assertEqual(protocol.encode(Timestamp(1507638896, 12345)), '2017-10-10T12:34:56.000012')


        with self.assertRaises(ValidationError):
            protocol.decode('yesterday')