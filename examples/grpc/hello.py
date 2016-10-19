from venom.fields import String
from venom.message import Message
from venom.rpc import Stub
from venom.rpc.stub import RPC


class HelloRequest(Message):
    name = String()


class HelloResponse(Message):
    message = String()


class HelloRemote(Stub):
    say_hello = RPC(HelloRequest, HelloResponse)
