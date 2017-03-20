from venom.fields import String
from venom.message import Message
from venom.rpc import Stub
from venom.rpc import rpc
from venom.rpc.stub import RPC


class HelloRequest(Message):
    name = String()


class HelloResponse(Message):
    message = String()


class HelloRemote(Stub):
    @rpc
    def say_hello(self, request: HelloRequest) -> HelloResponse:
        raise NotImplementedError
