
import json
from unittest import SkipTest

from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from venom import Message
from venom.fields import Int64, String, Int32
from venom.rpc import Service, http
from venom.rpc import rpc
from venom.rpc.comms.aiohttp import create_app
from venom.rpc.test_utils import mock_venom


class AioHTTPSimpleServerTestCase(AioHTTPTestCase):
    def get_app(self):
        class Snake(Message):
            id = Int64()
            name = String()
            size = Int32()

        class SnakeService(Service):
            @http.POST('.', request=Snake)
            def create(self, name: str, size: int = 2) -> Snake:
                # TODO document or fix inconsistent behavior of passing request message vs deconstructing request
                #      with required args with regard to setting defaults.
                return Snake(1, name, size)

            @http.POST
            def all_hiss(self) -> None:
                pass

            @http.POST('./{id:\d+}/hiss', request=Snake)
            def hiss(self, id: int) -> None:
                pass

            @http.GET('./{id:\d+}', request=Snake)
            def read(self, id: int) -> Snake:
                return Snake(id, 'Snek #{}'.format(id))

            # TODO support Repeat!
            # @http.GET('/')
            # def snakes(self) -> :

            @http.GET('./status/500')
            def http500(self) -> None:
                raise ValueError('No!')

            @http.GET('./status/501')
            def http501(self) -> None:
                raise NotImplementedError

        venom = mock_venom(SnakeService)
        return create_app(venom)

    @unittest_run_loop
    async def test_route_POST(self):
        response = await self.client.post("/snake", data=json.dumps({}))

        self.assertEqual(200, response.status)
        self.assertEqual({'id': 1, 'name': '', 'size': 2}, await response.json())

        response = await self.client.post("/snake", data=json.dumps({'name': 'Snek', 'size': 9001}))

        self.assertEqual(200, response.status)
        self.assertEqual({'id': 1, 'name': 'Snek', 'size': 9001}, await response.json())

    @unittest_run_loop
    async def test_route_POST_empty(self):
        response = await self.client.post("/snake/all-hiss")
        self.assertEqual(204, response.status)
        self.assertEqual('', await response.text())
        self.assertEqual(None, await response.json())

        response = await self.client.post("/snake/5/hiss", data=json.dumps({}))
        self.assertEqual(204, response.status)
        self.assertEqual('', await response.text())
        self.assertEqual(None, await response.json())

    @unittest_run_loop
    async def test_route_GET(self):
        response = await self.client.get("/snake/3")
        self.assertEqual(200, response.status)
        self.assertEqual({'id': 3, 'name': 'Snek #3'}, await response.json())

        # TODO support Repeat!
        # response = await self.client.get("/snakes")
        # self.assertEqual(200, response.status)
        # self.assertEqual([{}, ...], await response.json())

    @unittest_run_loop
    async def test_route_404_error(self):
        response = await self.client.get("/snake/bite")
        self.assertEqual(404, response.status)

    @unittest_run_loop
    async def test_route_400_error(self):
        response = await self.client.post("/snake", data=json.dumps({'name': 42}))
        self.assertEqual(400, response.status)
        self.assertEqual({'description': "42 is not of type 'str'", 'path': 'name', 'status': 400},
                         await response.json())

    @SkipTest
    @unittest_run_loop
    async def test_route_500_error(self):
        # TODO not supported yet
        response = await self.client.get("/snake/status/500")
        self.assertEqual(500, response.status)
        self.assertEqual({'message': None, 'path': 'name', 'status': 400},
                         await response.json())

    @unittest_run_loop
    async def test_route_501_error(self):
        # TODO not supported yet
        response = await self.client.get("/snake/status/501")
        # self.assertEqual(500, response.status)
        self.assertEqual({'status': 501, 'description': 'Not Implemented'}, await response.json())
