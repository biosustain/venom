from typing import List, Dict
from unittest import SkipTest
from unittest import TestCase

from venom import Empty, Message
from venom.common import Int64ValueConverter, Int32ValueConverter, IntegerValueConverter, StringValueConverter
from venom.common import IntegerValue, StringValue
from venom.fields import Int64, String, Repeat
from venom.rpc.inspection import magic


class InspectionTestCase(TestCase):
    def test_magic_return_empty(self):
        def func(self, request: Empty) -> Empty:
            return Empty()

        inspect = magic(func)
        # self.assertEqual(i.request, Empty)
        self.assertEqual(inspect.response, Empty)
        self.assertEqual(inspect.invokable, func, msg='No wrapping necessary')
        self.assertEqual(inspect.invokable(None, Empty()), Empty())

        def func(self, request: Empty) -> None:
            return None

        inspect = magic(func)
        self.assertEqual(inspect.response, Empty)
        self.assertNotEqual(inspect.invokable, func)
        self.assertEqual(inspect.invokable(None, Empty()), Empty())

        def func(self, request: Empty):
            return 42

        inspect = magic(func, response=Empty)
        self.assertEqual(inspect.response, Empty)
        self.assertNotEqual(inspect.invokable, func)
        self.assertEqual(inspect.invokable(None, Empty()), Empty())

        def func(self, request: Empty):
            return 42

        inspect = magic(func)
        self.assertEqual(inspect.response, Empty)
        self.assertNotEqual(inspect.invokable, func)
        self.assertEqual(inspect.invokable(None, Empty()), Empty())

    def test_magic_return_value(self):
        def func(self) -> IntegerValue:
            return IntegerValue(42)

        inspect = magic(func)
        self.assertEqual(inspect.response, IntegerValue)
        self.assertEqual(inspect.request, Empty)
        self.assertEqual(inspect.invokable(None, Empty()), IntegerValue(42))

        # NOTE: This uses converters.

        def func(self) -> int:
            return 42

        inspect = magic(func, converters=[Int64ValueConverter(), Int32ValueConverter()])
        self.assertEqual(inspect.response, IntegerValue)
        self.assertEqual(inspect.request, Empty)
        self.assertEqual(inspect.invokable(None, Empty()), IntegerValue(42))

        def func(self) -> str:
            return 'foo'

        inspect = magic(func, converters=[IntegerValueConverter(), StringValueConverter()])
        self.assertEqual(inspect.response, StringValue)
        self.assertEqual(inspect.request, Empty)
        self.assertEqual(inspect.invokable(None, Empty()), StringValue('foo'))

        with self.assertRaises(RuntimeError):
            def func(self) -> int:
                return 42

            inspect = magic(func, converters=[StringValueConverter()])

    @SkipTest
    def test_magic_map_return_value(self):
        def func(self) -> Dict[str, int]:
            return {"a": 1}

    @SkipTest
    def test_magic_repeat_return_value(self):
        def func(self) -> List[int]:
            return [1, 2, 3]

    def test_magic_request_message(self):
        def func(self, request: IntegerValue) -> IntegerValue:
            return IntegerValue(request.value)

        inspect = magic(func)
        self.assertEqual(inspect.response, IntegerValue)
        self.assertEqual(inspect.request, IntegerValue)
        self.assertEqual(inspect.invokable(None, IntegerValue(42)), IntegerValue(42))

    def test_magic_request_message_unpack(self):
        def func(self, value: int) -> IntegerValue:
            return IntegerValue(value)

        inspect = magic(func, request=IntegerValue)
        self.assertEqual(inspect.response, IntegerValue)
        self.assertEqual(inspect.request, IntegerValue)
        self.assertEqual(inspect.invokable(None, IntegerValue(42)), IntegerValue(42))

        def func(self) -> IntegerValue:
            return IntegerValue(42)

        inspect = magic(func, request=IntegerValue)
        self.assertEqual(inspect.response, IntegerValue)
        self.assertEqual(inspect.request, IntegerValue)
        self.assertEqual(inspect.invokable(None, IntegerValue(42)), IntegerValue(42))

        class Snake(Message):
            name = String()
            size = Int64()

        def func(self, name: str, size: int, hungry: bool = True) -> Snake:
            return Snake(name, size - hungry)

        inspect = magic(func, request=Snake)
        self.assertEqual(inspect.response, Snake)
        self.assertEqual(inspect.request, Snake)
        self.assertEqual(inspect.invokable(None, Snake('snek', 3)), Snake('snek', 2))

        with self.assertRaises(RuntimeError):
            def func() -> IntegerValue:
                return IntegerValue(42)

            inspect = magic(func, request=IntegerValue)

    @SkipTest
    def test_magic_request_message_unpack_map_param(self):
        class Pairs(Message):
            pairs = Repeat(String())

        def func(self, pairs: Dict[str, str]) -> Empty:
            pass

    @SkipTest
    def test_magic_request_message_unpack_repeat_param(self):
        class Items(Message):
            values = Repeat(String())

        def func(self, values: List[str]) -> Empty:
            pass

    @SkipTest
    def test_magic_request_message_autogenerate(self):
        # TODO

        def func(self, request: int) -> IntegerValue:
            return IntegerValue(request)

        inspect = magic(func)
        self.assertEqual(inspect.response, IntegerValue)
        self.assertEqual(inspect.request, IntegerValue)
        self.assertEqual(inspect.invokable(None, IntegerValue(42)), IntegerValue(42))

        # def func(self, a: int64, b: int64) -> IntegerValue:
        #     return IntegerValue(a + b)
        #
        # inspect = magic(func)
        # # self.assertEqual(inspect.response, IntegerValue)
        # self.assertEqual(inspect.request, IntegerValue)
        # self.assertEqual(inspect.invokable(None, IntegerValue(42)), IntegerValue(42))
