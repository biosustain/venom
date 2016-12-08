from venom import Empty
from venom.rpc.stub import Stub, RPC
from venom.rpc.test_utils import AioTestCase


class StubTestCase(AioTestCase):

    def test_stub_rpc(self):
        class PetStub(Stub):
            pet = RPC(Empty, Empty)

        self.assertEqual(set(PetStub.__methods__.keys()), {'pet'})
        self.assertEqual(PetStub.__methods__['pet'], PetStub.pet)
        self.assertEqual(PetStub.pet.request, Empty)
        self.assertEqual(PetStub.pet.response, Empty)
        self.assertEqual(PetStub.pet.name, 'pet')

    async def test_rpc_invoke(self):
        class PetStub(Stub):
            pet = RPC(Empty, Empty)

        with self.assertRaises(NotImplementedError):
            await PetStub().pet(Empty())

        with self.assertRaises(NotImplementedError):
            await PetStub.pet.invoke(PetStub(), Empty())
