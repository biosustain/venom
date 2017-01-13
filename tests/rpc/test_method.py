from collections import namedtuple

from venom import Empty
from venom import Message
from venom.converter import Converter
from venom.fields import Int32, String
from venom.rpc import Service, rpc
from venom.rpc.method import HTTPVerb
from venom.rpc.stub import Stub, RPC
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

            def convert(self, message: SnakeMessage) -> Snake:
                return Snake(message.name, message.size)

            def format(self, value: Snake) -> SnakeMessage:
                return SnakeMessage(name=value.name, size=value.size)

        class SnakeStub(Stub):
            grow = RPC(SnakeMessage, SnakeMessage)

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

        self.assertEqual(SnakeService().grow(Snake('snek', 2)), Snake('snek', 3))
        self.assertEqual(await SnakeService.grow.invoke(SnakeService(), SnakeMessage(name='snek', size=2)),
                         SnakeMessage(name='snek', size=3))
        self.assertEqual(await SnakeService.grow.invoke(SnakeService(), SnakeMessage(name='snek')),
                         SnakeMessage(name='snek', size=1))

    def test_method_http(self):
        class FooService(Service):
            pass
        self.assertEqual(RPC(Empty, Empty, name='bar').http_rule(FooService), '/foo/bar')
        self.assertEqual(RPC(Empty, Empty, name='foo').http_verb, HTTPVerb.POST)
        self.assertEqual(RPC.http.GET('./bar', Empty, Empty).http_rule(FooService), '/foo/bar')
        self.assertEqual(RPC.http.POST('./foo', Empty, Empty).http_verb, HTTPVerb.POST)
        self.assertEqual(RPC.http.DELETE('./foo', Empty, Empty).http_verb, HTTPVerb.DELETE)

    def test_method_http_rule_params(self):
        class Snake(Message):
            id = Int32()
            name = String()
            size = Int32()

        self.assertEqual(RPC.http.GET('./', Empty, Empty).http_path_params(), set())
        self.assertEqual(RPC.http.GET('./{id}', Snake, Snake).http_path_params(), {'id'})
        self.assertEqual(RPC.http.GET('./{name}/{id}', Snake, Snake).http_path_params(), {'id', 'name'})
