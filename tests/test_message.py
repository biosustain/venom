from collections import OrderedDict
from unittest import TestCase, SkipTest
from venom.message import Message
from venom.fields import String, Integer


class MessageTestCase(TestCase):
    def test_message_fields(self):
        class Pet(Message):
            sound = String()

        self.assertEqual({
            'sound': String(attribute='sound')
        }, Pet.__fields__)

    def test_message_instance(self):
        class Pet(Message):
            sound = String()

        cat = Pet(sound="meow")

        self.assertEqual("meow", cat.sound)
        self.assertEqual({'sound': 'meow'}, dict(cat))

    def test_message_from_obj(self):
        class Pet(Message):
            name = String(attribute="alias")

        self.assertEqual("Foo", Pet.from_object({"name": "Foo"}).name)

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
