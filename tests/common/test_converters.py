# TODO Test DateTime and Date converters
from datetime import datetime
from unittest import TestCase

from venom import Message
from venom.common import Timestamp
from venom.common.fields import DateTime
from venom.converter import Converter
from venom.fields import ConverterField


class ConverterFieldsTestCase(TestCase):

    def test_datetime(self):
        class Foo(Message):
            created_at = DateTime()

        message = Foo()

        self.assertEqual(message.get('created_at'), Timestamp())
        self.assertEqual(message.created_at, datetime(1970, 1, 1, 0, 0))

        message.created_at = datetime(2017, 2, 1, 15, 50, 1)

        self.assertEqual(message.get('created_at'), Timestamp(seconds=1485964201, nanos=0))
        self.assertEqual(message.created_at, datetime(2017, 2, 1, 15, 50, 1))

    def test_scalar(self):
        class StringConverter(Converter[int, str]):
            wire = int
            python = str

            def convert(self, value: int) -> str:
                return str(value)

            def format(self, value: str) -> int:
                return int(value)

        class Foo(Message):
            int_id = ConverterField(StringConverter())

        message = Foo()
        self.assertEqual(message.get('int_id'), 0)
        self.assertEqual(message.int_id, '0')

        message.int_id = '42'
        self.assertEqual(message.get('int_id'), 42)
