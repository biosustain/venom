from venom.fields import String, Bool
from venom.message import Message
from venom.rpc import Stub
from venom.rpc.stub import RPC


class HelloRequest(Message):
    name = String()
    shout = Bool()


class HelloResponse(Message):
    message = String()


class HelloStub(Stub):
    say_hello = RPC.http.POST('/greet/{name}', HelloRequest, HelloResponse)
