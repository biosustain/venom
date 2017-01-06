from collections import namedtuple
from typing import List, Dict
from unittest import SkipTest

from venom import Empty, Message
from venom.common import Int64ValueConverter, Int32ValueConverter, IntegerValueConverter, StringValueConverter
from venom.common import IntegerValue, StringValue
from venom.fields import Int64, String, Repeat, Integer, Map
from venom.rpc.inspection import magic_normalize
from venom.rpc.resolver import Resolver
from venom.rpc.test_utils import AioTestCase


class InspectionTestCase(AioTestCase):
    async def test_magic_return_empty(self):
        def func(self, request: Empty) -> Empty:
            return Empty()

        inspect = magic_normalize(func)
        self.assertEqual(inspect.request, Empty)
        self.assertEqual(inspect.response, Empty)
        self.assertEqual(await inspect.invokable(None, Empty()), Empty())

        def func(self, request: Empty) -> None:
            return None

        inspect = magic_normalize(func)
        self.assertEqual(inspect.response, Empty)
        self.assertEqual(await inspect.invokable(None, Empty()), Empty())

        def func(self, request: Empty):
            return 42

        inspect = magic_normalize(func, response=Empty)
        self.assertEqual(inspect.response, Empty)
        self.assertEqual(await inspect.invokable(None, Empty()), Empty())

        def func(self, request: Empty):
            return 42

        inspect = magic_normalize(func)
        self.assertEqual(inspect.response, Empty)
        self.assertEqual(await inspect.invokable(None, Empty()), Empty())

    async def test_magic_return_value(self):
        def func(self) -> IntegerValue:
            return IntegerValue(42)

        inspect = magic_normalize(func)
        self.assertEqual(inspect.response, IntegerValue)
        self.assertEqual(inspect.request, Empty)
        self.assertEqual(await inspect.invokable(None, Empty()), IntegerValue(42))

        # NOTE: This uses converters.

        def func(self) -> int:
            return 42

        inspect = magic_normalize(func, converters=[Int64ValueConverter(), Int32ValueConverter()])
        self.assertEqual(inspect.response, IntegerValue)
        self.assertEqual(inspect.request, Empty)
        self.assertEqual(await inspect.invokable(None, Empty()), IntegerValue(42))

        def func(self) -> str:
            return 'foo'

        inspect = magic_normalize(func, converters=[IntegerValueConverter(), StringValueConverter()])
        self.assertEqual(inspect.response, StringValue)
        self.assertEqual(inspect.request, Empty)
        self.assertEqual(await inspect.invokable(None, Empty()), StringValue('foo'))

        with self.assertRaises(RuntimeError):
            def func(self) -> int:
                return 42

            inspect = magic_normalize(func, converters=[StringValueConverter()])

    @SkipTest
    def test_magic_map_return_value(self):
        def func(self) -> Dict[str, int]:
            return {"a": 1}

    @SkipTest
    def test_magic_repeat_return_value(self):
        def func(self) -> List[int]:
            return [1, 2, 3]

    async def test_magic_request_message(self):
        def func(self, request: IntegerValue) -> IntegerValue:
            return IntegerValue(request.value)

        inspect = magic_normalize(func)
        self.assertEqual(inspect.response, IntegerValue)
        self.assertEqual(inspect.request, IntegerValue)
        self.assertEqual(await inspect.invokable(None, IntegerValue(42)), IntegerValue(42))

    async def test_magic_request_message_unpack(self):
        def func(self, value: int) -> IntegerValue:
            return IntegerValue(value)

        inspect = magic_normalize(func, request=IntegerValue)
        self.assertEqual(inspect.response, IntegerValue)
        self.assertEqual(inspect.request, IntegerValue)
        self.assertEqual(await inspect.invokable(None, IntegerValue(42)), IntegerValue(42))

        def func(self) -> IntegerValue:
            return IntegerValue(42)

        inspect = magic_normalize(func, request=IntegerValue)
        self.assertEqual(inspect.response, IntegerValue)
        self.assertEqual(inspect.request, IntegerValue)
        self.assertEqual(await inspect.invokable(None, IntegerValue(42)), IntegerValue(42))

        class Snake(Message):
            name = String()
            size = Int64()

        def func(self, name: str, size: int, hungry: bool = True) -> Snake:
            return Snake(name, size - hungry)

        inspect = magic_normalize(func, request=Snake)
        self.assertEqual(inspect.response, Snake)
        self.assertEqual(inspect.request, Snake)
        self.assertEqual(await inspect.invokable(None, Snake('snek', 3)), Snake('snek', 2))

        with self.assertRaises(RuntimeError):
            def func() -> IntegerValue:
                return IntegerValue(42)

            inspect = magic_normalize(func, request=IntegerValue)

    def test_magic_request_message_unpack_map_param(self):
        class Pairs(Message):
            pairs = Map(String())

        def func(self, pairs: Dict[str, str]) -> Empty:
            pass

        inspect = magic_normalize(func, request=Pairs)

    def test_magic_request_message_unpack_repeat_param(self):
        class StringList(Message):
            values = Repeat(String())

        class IntegerList(Message):
            values = Repeat(Integer())

        def func(self, values: List[str]) -> Empty:
            pass

        inspect = magic_normalize(func, request=StringList)
        self.assertEqual(inspect.response, Empty)
        self.assertEqual(inspect.request, StringList)

        with self.assertRaises(RuntimeError):
            inspect = magic_normalize(func, request=IntegerList)

    @SkipTest
    def test_magic_request_message_autogenerate(self):
        # TODO

        def func(self, request: int) -> IntegerValue:
            return IntegerValue(request)

        inspect = magic_normalize(func)
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

    async def test_magic_specified_resolver_args(self):
        Foo = namedtuple('Foo', ['service', 'request'])

        class FooResolver(Resolver):
            async def resolve(self, service, request):
                return Foo(service, request)

        def func(service_self, foo: Foo, request: IntegerValue) -> IntegerValue:
            self.assertEqual(service_self, None)
            self.assertEqual(foo.service, service_self)
            self.assertEqual(foo.request, request)
            return IntegerValue(request.value)

        inspect = magic_normalize(func, additional_args=(FooResolver,))
        self.assertEqual(inspect.response, IntegerValue)
        self.assertEqual(inspect.request, IntegerValue)
        self.assertEqual(await inspect.invokable(None, IntegerValue(42)), IntegerValue(42))
