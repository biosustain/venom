from unittest import TestCase

from venom import Empty
from venom.rpc.stub import Stub, RPC


class StubTestCase(TestCase):

    def test_stub_rpc(self):
        class PetStub(Stub):
            pet = RPC(Empty, Empty)

        self.assertEqual(set(PetStub.__methods__.keys()), {'pet'})
        self.assertEqual(PetStub.__methods__['pet'], PetStub.pet)
        self.assertEqual(PetStub.pet.request, Empty)
        self.assertEqual(PetStub.pet.response, Empty)
        self.assertEqual(PetStub.pet.name, 'pet')

    def test_rpc_invoke(self):
        class PetStub(Stub):
            pet = RPC(Empty, Empty)

        with self.assertRaises(NotImplementedError):
            PetStub().pet(Empty())

        with self.assertRaises(NotImplementedError):
            PetStub.pet.invoke(PetStub(), Empty())
