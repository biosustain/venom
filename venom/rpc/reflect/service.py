from venom.rpc import Service, Venom
from venom.rpc import http
from venom.rpc.reflect.openapi import make_openapi_schema
from venom.rpc.reflect.reflect import Reflect
from venom.rpc.reflect.stubs import ReflectStub, OpenAPISchema


class ReflectService(Service):
    class Meta:
        stub = ReflectStub

    def __init__(self, venom: 'venom.rpc.Venom' = None) -> None:
        super().__init__(venom)
        self.reflect = Reflect(
            title=venom.options.get('title', 'API'),
            version=venom.options.get('version', '1.0.0'),
        )

        for service in venom:
            self._reflect_service(venom, service)

        Venom.on_add_public_service.connect(self._reflect_service, sender=venom)

    def _reflect_service(self, sender: Venom, service: Service):
        self.reflect.add(service)

    @http.GET('/openapi.json')
    def get_openapi_schema(self) -> OpenAPISchema:
        return make_openapi_schema(self.reflect)
