from unittest import TestCase

from venom.rpc import rpc, Service


class ServiceTestCase(TestCase):

    def test_service_methods(self):
        class PetService(Service):
            @rpc
            def pet(self) -> None:
                pass

        self.assertEqual(set(PetService.__methods__.keys()), {"pet"})

    def test_service_methods_inheritance(self):
        class PetService(Service):
            @rpc
            def pet(self) -> None:
                pass

        class SnakeService(PetService):
            @rpc
            def boop(self) -> None:
                pass

        self.assertEqual(set(SnakeService.__methods__.keys()), {"pet", "boop"})
