from unittest import SkipTest

from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from venom import Empty
from venom import Message
from venom.exceptions import NotImplemented_
from venom.fields import String
from venom.rpc import RPC
from venom.rpc import Service, rpc, Venom
from venom.rpc import Stub
from venom.rpc.comms.aiohttp import create_app, Client


class HelloRequest(Message):
    name = String()


class HelloResponse(Message):
    message = String()


class GreetingStub(Stub):
    greet = RPC(HelloRequest, HelloResponse)
    goodbye = RPC(Empty, Empty)


class AioHTTPEndToEndTestCase(AioHTTPTestCase):
    def get_app(self, loop):

        class GreetingService(Service):
            class Meta:
                stub = GreetingStub

            @rpc(request=HelloRequest)
            def greet(self, name: str) -> HelloResponse:
                return HelloResponse('Hello, {}!'.format(name))

        venom = Venom()
        venom.add(GreetingService)
        return create_app(venom, loop=loop)

    @unittest_run_loop
    async def test_client_success(self):

        venom = Venom()
        venom.add(GreetingStub, Client, 'http://127.0.0.1:{}'.format(self.client.port), session=self.client.session)

        self.assertEqual(HelloResponse('Hello, Alice!'), await venom
                         .get_instance(GreetingStub)
                         .greet(HelloRequest('Alice')))

    @unittest_run_loop
    async def test_client_exception(self):
        venom = Venom()
        venom.add(GreetingStub, Client, 'http://127.0.0.1:{}'.format(self.client.port), session=self.client.session)

        with self.assertRaises(NotImplemented_):
            await venom.get_instance(GreetingStub).goodbye(Empty)


