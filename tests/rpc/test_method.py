from collections import namedtuple
from unittest import SkipTest

from venom import Empty
from venom import Message
from venom.common import Value, BoolValue
from venom.common.types import JSONValue
from venom.converter import Converter
from venom.fields import Int32, String
from venom.rpc import Service, rpc
from venom.rpc.method import HTTPVerb, MethodDescriptor
from venom.rpc.stub import Stub
from venom.rpc.test_utils import AioTestCase


class MethodTestCase(AioTestCase):
    async def test_method_override(self):
        Snake = namedtuple('Snake', ('name', 'size'))

        class SnakeMessage(Message):
            name = String()
            size = Int32()

        class SnakeConverter(Converter):
            wire = SnakeMessage
            python = Snake

            def resolve(self, message: SnakeMessage) -> Snake:
                return Snake(message.name, message.size)

            def format(self, value: Snake) -> SnakeMessage:
                return SnakeMessage(name=value.name, size=value.size)

        class SnakeStub(Stub):
            @rpc(SnakeMessage, SnakeMessage)
            def grow(self): pass

        self.assertEqual(set(SnakeStub.__methods__.keys()), {"grow"})
        self.assertEqual(SnakeStub.__methods__['grow'].request, SnakeMessage)
        self.assertEqual(SnakeStub.__methods__['grow'].response, SnakeMessage)

        # TODO test without stub (auto-generated request message)
        class SnakeService(Service):
            class Meta:
                converters = [SnakeConverter()]
                stub = SnakeStub

            @rpc
            def grow(self, request: Snake) -> Snake:
                return Snake(name=request.name, size=request.size + 1)

        self.assertEqual(await SnakeService().grow(SnakeMessage('snek', 2)), SnakeMessage('snek', 3))
        self.assertEqual(await SnakeService.grow.invoke(SnakeService(), SnakeMessage(name='snek', size=2)),
                         SnakeMessage(name='snek', size=3))
        self.assertEqual(await SnakeService.grow.invoke(SnakeService(), SnakeMessage(name='snek')),
                         SnakeMessage(name='snek', size=1))

    def test_method_http(self):
        class FooService(Service):
            pass

        self.assertEqual(MethodDescriptor(Empty, Empty).prepare(FooService(), 'bar').http_path, '/foo/bar')
        self.assertEqual(MethodDescriptor(Empty, Empty).prepare(FooService(), 'foo').http_method, HTTPVerb.POST)
        self.assertEqual(MethodDescriptor(Empty, Empty,
                                          http_path='./bar').prepare(FooService(), 'foo').http_path, '/foo/bar')

        self.assertEqual(MethodDescriptor(Empty, Empty, http_method=HTTPVerb.POST).http_method, HTTPVerb.POST)
        self.assertEqual(MethodDescriptor(Empty, Empty, http_method=HTTPVerb.DELETE).http_method, HTTPVerb.DELETE)

    def test_method_http_rule_params(self):
        class Snake(Message):
            id = Int32()
            name = String()
            size = Int32()

        class FooService(Service):
            pass

        self.assertEqual(MethodDescriptor(Empty, Empty)
                         .prepare(FooService(), 'foo')
                         .http_path_parameters(), set())
        self.assertEqual(MethodDescriptor(Snake, Snake, http_path='./{id}')
                         .prepare(FooService(), 'foo')
                         .http_path_parameters(), {'id'})
        self.assertEqual(MethodDescriptor(Snake, Snake, http_path='./{name}/{id}')
                         .prepare(FooService(), 'foo')
                         .http_path_parameters(), {'id', 'name'})

    @SkipTest
    async def test_json_method(self):
        class FooService(Service):
            @rpc
            def get_json(self) -> JSONValue:
                return {"foo": True}

        self.assertEqual(await FooService.get_json.invoke(FooService(), Empty()),
                         Value(bool_value=BoolValue(True)))


