from venom.fields import String
from venom.message import Message
from venom.rpc import Remote
from venom.rpc.remote import RPC


class HelloRequest(Message):
    name = String()


class HelloResponse(Message):
    message = String()


class HelloRemote(Remote):
    say_hello = RPC(HelloRequest, HelloResponse)
