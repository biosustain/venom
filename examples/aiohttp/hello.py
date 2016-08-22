

from venom.fields import String, Boolean
from venom.message import Message
from venom.rpc import Remote
from venom.rpc.method import HTTPMethod
from venom.rpc.remote import RPC


class HelloRequest(Message):
    name = String()
    shout = Boolean()


class HelloResponse(Message):
    message = String()


class HelloRemote(Remote):
    say_hello = RPC(HelloRequest, HelloResponse, http_method=HTTPMethod.POST, http_rule='/greet/{name}')
    #say_hello = RPC.http.GET('/greet/{name}', HelloRequest, HelloResponse)
