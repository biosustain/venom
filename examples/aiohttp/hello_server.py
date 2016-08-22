from aiohttp import web

from venom.rpc import Service, Venom
from venom.rpc.comms.aiohttp import create_app
from venom.rpc.method import http
from hello import HelloRequest, HelloResponse


class HelloService(Service):
    @http.POST('/greet/{name}', request=HelloRequest, response=HelloResponse)
    def say_hello(self, request: HelloRequest) -> HelloResponse:
        message = "Hello, {}!".format(request.name)

        if request.shout:
            message = message.upper()

        return HelloResponse(message=message)


venom = Venom()
venom.add(HelloService)

app = create_app(venom)

if __name__ == '__main__':
    web.run_app(app)
