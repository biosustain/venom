from typing import List
from unittest import SkipTest

from venom import Empty
from venom.common import StringValue, Bool, Repeat
from venom.exceptions import NotImplemented_
from venom.fields import String
from venom.message import fields
from venom.rpc import rpc
from venom.rpc.stub import Stub, RPC
from venom.rpc.test_utils import AioTestCase


class StubTestCase(AioTestCase):

    def test_stub_rpc(self):
        class PetStub(Stub):
            @rpc
            def pet(self, request: Empty) -> Empty:
                raise NotImplementedError

        self.assertEqual(set(PetStub.__methods__.keys()), {'pet'})
        self.assertEqual(PetStub.__methods__['pet'], PetStub.pet)
        self.assertEqual(PetStub.pet.request, Empty)
        self.assertEqual(PetStub.pet.response, Empty)
        self.assertEqual(PetStub.pet.name, 'pet')

    def test_stub_rpc_require_auto(self):
        with self.assertRaises(RuntimeError):
            class GreeterStub(Stub):
                @rpc
                def greet(self, name: str) -> str:
                    raise NotImplementedError

    def test_stub_rpc_request_auto(self):
        class GreeterStub(Stub):
            @rpc(auto=True)
            def greet(self, name: str, shout: bool = False) -> str:
                raise NotImplementedError

        self.assertEqual(GreeterStub.greet.request.__meta__.name, 'GreetRequest')
        self.assertEqual(tuple(fields(GreeterStub.greet.request)), (
            String(name='name'),
            Bool(name='shout'),
        ))

        self.assertEqual(GreeterStub.greet.response, StringValue)
        self.assertEqual(GreeterStub.greet.name, 'greet')

    def test_stub_rpc_request_repeat_auto(self):
        class GreeterStub(Stub):
            @rpc(auto=True)
            def greet_many(self, names: List[str]) -> str:
                raise NotImplementedError

        self.assertEqual(GreeterStub.greet_many.request.__meta__.name, 'GreetManyRequest')
        self.assertEqual(tuple(fields(GreeterStub.greet_many.request)), (
            Repeat(String(), name='names'),
        ))

        self.assertEqual(GreeterStub.greet_many.response, StringValue)
        self.assertEqual(GreeterStub.greet_many.name, 'greet_many')

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
            pet = RPC(Empty, Empty)

        with self.assertRaises(NotImplementedError):
            await PetStub().pet(Empty())

        with self.assertRaises(NotImplemented_):
            await PetStub.pet.invoke(PetStub(), Empty())
