from unittest import TestCase

from venom.rpc import Service, Venom
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

        self.assertEqual(ReflectService.__manager__.services, {BeforeService, AfterService, ReflectService})
