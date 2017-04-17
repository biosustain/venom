from typing import Type

from venom.rpc.method import MethodDescriptor
from venom.rpc.service import Service, ServiceMeta, ServiceManager


class StubManager(ServiceManager):
    def prepare_method(self, service: Type['Service'], method: MethodDescriptor, name: str):
        return method.stub(service, name)


class StubMeta(ServiceMeta):
    def __new__(metacls, what, bases=None, members=None):
        cls = super().__new__(metacls, what, bases, members)
        cls.__method_descriptors__ = {
            name: method.stub(cls, name)
            for name, method in cls.__method_descriptors__.items()
        }
        return cls


class Stub(Service, metaclass=StubMeta):
    class Meta:
        manager = StubManager
