from aiohttp import web

from examples.aiohttp.hello import HelloStub
from venom.rpc import Venom
from venom.rpc.comms.aiohttp import create_app, Client

venom = Venom()
venom.add(HelloStub, Client, 'http://localhost:8080', public=True)

app = create_app(venom)

if __name__ == '__main__':
    web.run_app(app, port=8081)
