import asyncio

from hello import HelloStub, HelloRequest
from venom.rpc.comms.aiohttp import Client

client = Client(HelloStub, 'http://localhost:5050')

async def request_say_hello(name):
    response = await client.invoke(HelloStub.say_hello, HelloRequest(name=name, shout=True))
    print('response:', response.message)

loop = asyncio.get_event_loop()
loop.run_until_complete(request_say_hello('world'))
