import time

import asyncio
from venom.rpc.comms.grpc import create_server
from venom.rpc.method import rpc
from hello import HelloRequest, HelloResponse
from venom.rpc import Service, Venom


class HelloService(Service):
    @rpc(request=HelloRequest, response=HelloResponse)
    async def say_hello(self, request: HelloRequest) -> HelloResponse:
        await asyncio.sleep(5)
        return HelloResponse(message="Hello, {}!".format(request.name))


app = Venom()
app.add(HelloService)

server = create_server(app)

if __name__ == '__main__':
    server.add_insecure_port('[::]:50053')
    server.start()
    try:
        while True:
            time.sleep(24 * 60 * 60)
    except KeyboardInterrupt:
        server.stop(0)
