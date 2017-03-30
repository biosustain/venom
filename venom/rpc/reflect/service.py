from typing import Type

from venom.rpc import Service, Venom
from venom.rpc import http
from venom.rpc.reflect.openapi import make_openapi_schema
from venom.rpc.reflect.reflect import Reflect
from venom.rpc.reflect.stubs import ReflectStub, OpenAPISchema
from venom.rpc.service import ServiceManager
from venom.util import MetaDict


class ReflectServiceManager(ServiceManager):
    def __init__(self, meta: MetaDict, meta_changes: MetaDict):
        super().__init__(meta, meta_changes)
        self.reflect = Reflect()
        # TODO setup

    def reflect_service(self, sender: Venom, service: Service):
        self.reflect.add(service)
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
    def get_openapi_schema(self) -> OpenAPISchema:
        return make_openapi_schema(self.__manager__.reflect)
