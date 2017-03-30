from typing import List
from unittest import SkipTest

from venom import Empty
from venom.common import StringValue, Bool, Repeat
from venom.exceptions import NotImplemented_
from venom.fields import String
from venom.message import fields
from venom.rpc import rpc
from venom.rpc.method import MethodDescriptor, Method
from venom.rpc.stub import Stub
from venom.rpc.test_utils import AioTestCase


class StubTestCase(AioTestCase):
    def test_stub_rpc(self):
        class PetStub(Stub):
            @rpc
            def pet(self, request: Empty) -> Empty:
                raise NotImplementedError

        self.assertEqual(set(PetStub.__methods__.keys()), {'pet'})
        self.assertIsInstance(PetStub.__methods__['pet'], MethodDescriptor)

        stub = PetStub()
        self.assertIsInstance(stub.pet, Method)
        self.assertEqual(stub.pet.request, Empty)
        self.assertEqual(stub.pet.response, Empty)
        self.assertEqual(stub.pet.name, 'pet')

    def test_stub_rpc_require_auto(self):
        with self.assertRaises(RuntimeError):
            class GreeterStub(Stub):
                @rpc
                def greet(self, name: str) -> str:
                    raise NotImplementedError
            GreeterStub()

    def test_stub_rpc_request_auto(self):
        class GreeterStub(Stub):
            @rpc(auto=True)
            def greet(self, name: str, shout: bool = False) -> str:
                raise NotImplementedError

        self.assertEqual(GreeterStub().greet.request.__meta__.name, 'GreetRequest')
        self.assertEqual(tuple(fields(GreeterStub().greet.request)), (
            String(name='name'),
            Bool(name='shout'),
        ))

        self.assertEqual(GreeterStub().greet.response, StringValue)
        self.assertEqual(GreeterStub().greet.name, 'greet')

    def test_stub_rpc_request_repeat_auto(self):
        class GreeterStub(Stub):
            @rpc(auto=True)
            def greet_many(self, names: List[str]) -> str:
                raise NotImplementedError

        stub = GreeterStub()
        self.assertEqual(stub.greet_many.request.__meta__.name, 'GreetManyRequest')
        self.assertEqual(tuple(fields(stub.greet_many.request)), (
            Repeat(String(), name='names'),
        ))

        self.assertEqual(stub.greet_many.response, StringValue)
        self.assertEqual(stub.greet_many.name, 'greet_many')

    @SkipTest
    def test_stub_rpc_response_repeat_auto(self):
        class GreeterStub(Stub):
            @rpc(auto=True)
            def get_greetings(self) -> List[str]:
                raise NotImplementedError

        self.assertEqual(GreeterStub.get_greetings.response.__meta__.name, 'GetGreetingsResponse')
        self.assertEqual(tuple(fields(GreeterStub.get_greetings.response)), (
            Repeat(String(), name='values')
        ))

        self.assertEqual(GreeterStub.greet.response, StringValue)
        self.assertEqual(GreeterStub.greet.name, 'get_greetings')

    async def test_rpc_invoke(self):
        class PetStub(Stub):
            @rpc
            def pet(self):
                pass

        with self.assertRaises(NotImplemented_):
            await PetStub().pet(Empty())
