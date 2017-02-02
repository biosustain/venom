# TODO Test DateTime and Date converters
from datetime import datetime
from unittest import TestCase

from venom import Message
from venom.common import Timestamp
from venom.common.fields import DateTime


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

