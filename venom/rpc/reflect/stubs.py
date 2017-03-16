from venom.rpc import Stub
from venom.rpc import http


class ReflectStub(Stub):

    @http.GET('/openapi.json')
    def get_openapi_schema(self):
        raise NotImplementedError()
