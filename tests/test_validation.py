from unittest import TestCase

from venom.common import IntegerValue
from venom.exceptions import ValidationError
from venom.fields import Field, RepeatField
from venom.message import Message
from venom.validation import Schema, MessageValidator


class ValidationTestCase(TestCase):

    def test_validate_string_length(self):
        class HelloRequest(Message):
            name = Field(str, schema=Schema(min_length=3, max_length=5))

        validator = MessageValidator(HelloRequest)

        with self.assertRaises(ValidationError) as ctx:
            validator.validate(HelloRequest('x'))

        self.assertEquals(ctx.exception.args[0], "'x' is too short")
        self.assertEquals(ctx.exception.path, ['name'])

        with self.assertRaises(ValidationError) as ctx:
            validator.validate(HelloRequest('x' * 10))

        self.assertEquals(ctx.exception.args[0], "'xxxxxxxxxx' is too long")
        self.assertEquals(ctx.exception.path, ['name'])

        for i in range(3, 5):
            validator.validate(HelloRequest('x' * i))

    def test_validate_repeat(self):
        class HelloRequest(Message):
            names = RepeatField(str, schema=Schema(min_length=3,
                                                   max_length=5,
                                                   max_items=5))

        validator = MessageValidator(HelloRequest)

        with self.assertRaises(ValidationError) as ctx:
            validator.validate(HelloRequest(['x']))

        self.assertEquals(ctx.exception.args[0], "'x' is too short")
        self.assertEquals(ctx.exception.path, ['names', 0])

        with self.assertRaises(ValidationError) as ctx:
            validator.validate(HelloRequest(['xxx', 'x' * 10]))

        self.assertEquals(ctx.exception.args[0], "'xxxxxxxxxx' is too long")
        self.assertEquals(ctx.exception.path, ['names', 1])

        validator.validate(HelloRequest(['x' * i for i in range(3, 5)]))

        with self.assertRaises(ValidationError) as ctx:
            validator.validate(HelloRequest(['xxx' for _ in range(10)]))

        self.assertEquals(ctx.exception.args[0], f"{repr(['xxx' for _ in range(10)])} is too long")
        self.assertEquals(ctx.exception.path, ['names'])
