from collections import OrderedDict
from typing import List
from unittest import TestCase, SkipTest

from venom.fields import String, Integer, repeated, Field
from venom.message import Message, from_object, items


class MessageTestCase(TestCase):
    def test_message_fields(self):
        class Pet(Message):
            sound: str

        self.assertEqual({
            'sound': String()
        }, Pet.__fields__)

    def test_message_instance(self):
        class Pet(Message):
            sound = String()

        cat = Pet(sound="meow")

        self.assertEqual("meow", cat.sound)
        self.assertEqual({'sound': 'meow'}, dict(items(cat)))

    def test_message_ordered_fields(self):
        class Pet(Message):
            sound = String()
            size = Integer()
            speed = Integer()
            age = Integer()

        self.assertIsInstance(Pet.__fields__, OrderedDict)
        self.assertEqual((
            'sound',
            'size',
            'speed',
            'age'
        ), tuple(Pet.__fields__.keys()))

    def test_message_type_hints(self):
        class Pet(Message):
            sounds: List[str]
            size: float
            speed: int
            age: int

        self.assertIsInstance(Pet.__fields__, OrderedDict)
        self.assertEqual((
            'sounds',
            'size',
            'speed',
            'age'
        ), tuple(Pet.__fields__.keys()))
        self.assertEqual({
            'sounds': repeated(String(), name='sounds'),
            'size': Field(float, name='size'),
            'speed': Field(int, name='speed'),
            'age': Field(int, name='age')
        }, Pet.__fields__)

    @SkipTest
    def test_message_one_of(self):
        class PetFilter(Message):
            nk = String()
            id = Integer()

            class Meta:
                one_of = (
                    ('nk', 'id')
                )

                # TODO
