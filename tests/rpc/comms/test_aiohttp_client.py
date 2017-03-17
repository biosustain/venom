from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from venom import Empty
from venom import Message
from venom.exceptions import NotImplemented_
from venom.fields import String
from venom.rpc import RPC
from venom.rpc import RequestContext
from venom.rpc import Service, http, Venom
from venom.rpc import Stub
from venom.rpc.comms.aiohttp import create_app, HTTPClient


class HelloRequest(Message):
    name = String()


class HelloResponse(Message):
    message = String()


class GreetingStub(Stub):
    greet = RPC.http('GET', './greet', HelloRequest, HelloResponse)
    goodbye = RPC(Empty, Empty)


class AioHTTPEndToEndTestCase(AioHTTPTestCase):
    def get_app(self, loop):
        class GreetingService(Service):
            class Meta:
                stub = GreetingStub

            @http.GET(request=HelloRequest)
            def greet(self, name: str) -> HelloResponse:
                return HelloResponse('Hello, {}!'.format(name))

        venom = Venom()
        venom.add(GreetingService)
        return create_app(venom, loop=loop)

    @unittest_run_loop
    async def test_client_success(self):
        venom = Venom()
        venom.add(GreetingStub, HTTPClient, 'http://127.0.0.1:{}'.format(self.client.port), session=self.client.session)

        with venom.get_request_context():
            self.assertEqual(HelloResponse('Hello, Alice!'), await venom
                             .get_instance(GreetingStub)
                             .greet(HelloRequest('Alice')))

    @unittest_run_loop
    async def test_client_exception(self):
        venom = Venom()
        venom.add(GreetingStub, HTTPClient, 'http://127.0.0.1:{}'.format(self.client.port), session=self.client.session)

        with venom.get_request_context():
            with self.assertRaises(NotImplemented_):
                await venom.get_instance(GreetingStub).goodbye(Empty())
