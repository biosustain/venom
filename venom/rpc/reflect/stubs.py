from venom import Message
from venom.rpc import Stub
from venom.rpc import http


class OpenAPISchema(Message):
    pass


class ReflectStub(Stub):

    @http.GET('/openapi.json')
    def get_openapi_schema(self) -> OpenAPISchema:
        raise NotImplementedError()
