from unittest import TestCase

from venom.fields import String, Field, Repeat, _RepeatValueProxy


class FieldsTestCase(TestCase):
    def test_field_equality(self):
        self.assertEqual(Field(int), Field(int))
        self.assertNotEqual(Field(str), Field(int))

        # TODO test comparison of other field attributes

    def test_field_descriptor(self):
        class M(dict):
            value = Field(str)

        self.assertIsInstance(M.value, Field)
        self.assertEqual(M.value, Field(str))

        M.value.name = 'value'

        m = M()
        self.assertEqual(m.value, str())

        m.value = 'foo'
        self.assertEqual('foo', m.value)
        self.assertEqual('foo', m['value'])

    def test_field_string(self):
        self.assertEqual(String(), Field(str))

    def test_repeat_field(self):
        class M(dict):
            items = Repeat(Field(str))

        M.items.name = 'items'

        m = M()

        with self.assertRaises(KeyError):
            m['items']

        self.assertIsInstance(m.items, _RepeatValueProxy)
        self.assertEqual(list(m.items), [])

        m.items.append(1)
        self.assertEqual(m['items'], [1])