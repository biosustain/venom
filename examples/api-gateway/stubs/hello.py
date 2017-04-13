from venom.fields import String, Bool
from venom.message import Message
from venom.rpc import Stub, http


class HelloRequest(Message):
    name: str
    shout: bool


class HelloResponse(Message):
    message: str


class HelloStub(Stub):
    @http.POST('/greet/{name}')
    def say_hello(self, request: HelloRequest) -> HelloResponse:
        raise NotImplementedError
