from unittest import TestCase
from venom.fields import Int, String, Bool
from venom.message import Message
from venom.rpc import Service, Venom, http
from venom.rpc.reflect.reflect import Reflect
from venom.rpc.reflect.service import ReflectService


class ReflectServiceTestCase(TestCase):
    def test_service_registration(self):
        class BeforeService(Service):
            pass

        class AfterService(Service):
            pass

        venom = Venom()
        venom.add(BeforeService)
        venom.add(ReflectService)
        venom.add(AfterService)

        self.assertEqual(venom.get_instance(ReflectService).reflect.services, {
            venom.get_instance(BeforeService),
            venom.get_instance(AfterService),
            venom.get_instance(ReflectService)
        })

    def test_reflect(self):

        class HelloRequest(Message):
            name = String()
            shout = Bool()

        class HelloResponse(Message):
            message = String()

        class HelloService(Service):
            @http.POST('./greet/{name}')
            def say_hello(self, request: HelloRequest) -> HelloResponse:
                text = "Hello, {}!".format(request.name)
                if request.shout:
                    text = text.upper()
                return HelloResponse(text)

        reflect = Reflect()
        reflect.add(HelloService)
        self.assertEqual(reflect.services, {HelloService})
        self.assertEqual(reflect.messages, {HelloRequest, HelloResponse})
        # TODO: check methods equality
