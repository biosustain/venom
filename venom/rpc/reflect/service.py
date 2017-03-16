from typing import Type

from venom.rpc import Service, Venom
from venom.rpc import http
from venom.rpc.reflect.stubs import ReflectStub
from venom.rpc.service import ServiceManager
from venom.util import MetaDict


class ReflectServiceManager(ServiceManager):
    def __init__(self, meta: MetaDict, meta_changes: MetaDict):
        super().__init__(meta, meta_changes)
        self.services = set()
        # TODO setup

    def reflect_service(self, sender: Venom, service: Type[Service]):
        self.services.add(service)
        pass  # TODO add reflection (venom specific)

    def register(self, venom: 'venom.Venom'):
        for service in venom:
            self.reflect_service(venom, service)
        Venom.on_add_public_service.connect(self.reflect_service, sender=venom)


class ReflectService(Service):
    class Meta:
        stub = ReflectStub
        manager = ReflectServiceManager

    @http.GET('/openapi.json')
    def get_openapi_schema(self):
        pass
