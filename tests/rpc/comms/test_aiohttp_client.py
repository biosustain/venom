from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from venom import Empty
from venom import Message
from venom.exceptions import NotImplemented_
from venom.fields import String
from venom.rpc import Service, http, Venom
from venom.rpc import Stub
from venom.rpc import rpc
from venom.rpc.comms.aiohttp import create_app, HTTPClient


class HelloRequest(Message):
    name = String()


class HelloResponse(Message):
    message = String()


class GreeterStub(Stub):
    @http.GET('./greet')
    def greet(self, request: HelloRequest) -> HelloResponse:
        pass

    @rpc
    def goodbye(self):
        pass


class AioHTTPEndToEndTestCase(AioHTTPTestCase):
    def get_app(self):
        class GreeterService(Service):
            class Meta:
                stub = GreeterStub

            @http.GET(request=HelloRequest)
            def greet(self, name: str) -> HelloResponse:
                return HelloResponse('Hello, {}!'.format(name))

        venom = Venom()
        venom.add(GreeterService)
        return create_app(venom)

    @unittest_run_loop
    async def test_client_success(self):
        venom = Venom()
        venom.add(GreeterStub, HTTPClient, 'http://127.0.0.1:{}'.format(self.client.port), session=self.client.session)

        with venom.get_request_context():
            greeter = venom.get_instance(GreeterStub)
            print('greeter:', greeter, greeter.greet)
            self.assertEqual(HelloResponse('Hello, Alice!'), await greeter.greet(HelloRequest('Alice')))

    @unittest_run_loop
    async def test_client_exception(self):
        venom = Venom()
        venom.add(GreeterStub, HTTPClient, 'http://127.0.0.1:{}'.format(self.client.port), session=self.client.session)

        with venom.get_request_context():
            with self.assertRaises(NotImplemented_):
                greeter = venom.get_instance(GreeterStub)
                await greeter.goodbye(Empty())
