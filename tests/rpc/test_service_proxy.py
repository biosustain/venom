
from unittest.mock import MagicMock

from venom.common import IntegerValue
from venom.rpc import RequestContext
from venom.rpc import Service, Venom, rpc
from venom.message import Message
from venom.fields import Integer
from venom.rpc import ServiceProxy
from venom.rpc.test_utils import MockVenom, AioTestCase, mock_instance


class ServiceProxyTestCase(AioTestCase):

    async def test_service_proxy_internal(self):
        """
        ServiceProxy usage scenario without any mocking.

        Note that this does not involve the API client and therefore the function signature is not regulated.
        """
        class LocationService(Service):
            @rpc
            async def exotic(self) -> str:
                return 'Bermuda'

        class ConspiracyService(Service):
            location = ServiceProxy('location')

            @rpc
            async def suspicious_area(self) -> str:
                return '{} Triangle'.format(await self.location.exotic())

        venom = Venom()
        venom.add(ConspiracyService)
        venom.add(LocationService)

        with venom.get_request_context():
            conspiracy = venom.get_instance('conspiracy')
            self.assertIsInstance(conspiracy, ConspiracyService)

            location = venom.get_instance('location')
            self.assertIsInstance(location, LocationService)

            self.assertEqual('Bermuda Triangle', await conspiracy.suspicious_area())

    async def test_service_proxy_mock_venom(self):
        """
        Mocking of all undeclared services using ServiceProxy.

        RPC calls are always asynchronous and it is recommended to only pass messages.
        """
        class BetweenRequest(Message):
            min = Integer()
            max = Integer()

        class ConspiracyService(Service):
            random = ServiceProxy('random')

            @rpc
            async def suspicious_area(self) -> str:
                x = await self.random.random(BetweenRequest(49, 100))
                print(x)
                return 'Area {}'.format((await self.random.random(BetweenRequest(49, 100))).value)

        venom = MockVenom()
        venom.add(ConspiracyService)

        with venom.get_request_context():
            conspiracy = venom.get_instance('conspiracy')
            conspiracy.random.random.side_effect = lambda request: IntegerValue(request.min + 2)
            self.assertIsInstance(conspiracy.random, MagicMock)
            self.assertEqual('Area 51', await conspiracy.suspicious_area())

    async def test_service_proxy_mock_instance(self):
        """
        ServiceProxy usage with mock_instance() which is as shorthand for setting up MockVenom with a service to test.
        """
        class ConspiracyService(Service):
            random = ServiceProxy('random')

            @rpc
            async def suspicious_area(self) -> str:
                return 'Area {}'.format((await self.random.random()).value)

        with RequestContext():
            conspiracy = mock_instance(ConspiracyService)
            conspiracy.random.random.return_value = IntegerValue(51)
            self.assertIsInstance(conspiracy.random, MagicMock)
            self.assertEqual('Area 51', await conspiracy.suspicious_area())
