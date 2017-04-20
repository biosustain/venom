from typing import Dict, ClassVar, Type

from venom.common import IntegerValueConverter, BoolValueConverter, DateTimeConverter, DateConverter
from venom.common import StringValueConverter, NumberValueConverter
from venom.rpc.context import RequestContextDescriptor
from venom.rpc.method import Method, MethodDescriptor
from venom.util import meta, MetaDict


class ServiceManager(object):
    def __init__(self, meta: MetaDict, meta_changes: MetaDict):
        self.meta = meta

    @staticmethod
    def get_service_name(cls_name: str) -> str:
        name = cls_name.lower()
        for postfix in ('service', 'stub'):
            if name.endswith(postfix):
                return name[:-len(postfix)]
        return name

    @classmethod
    def prepare_meta(cls, name: str, meta: MetaDict, meta_changes: MetaDict) -> MetaDict:
        if not meta_changes.get('name'):
            meta.name = cls.get_service_name(name)

        if not meta_changes.get('http_path', None):
            meta.http_path = f"/{meta.name.lower().replace('_', '-')}"
        return meta

    def prepare_method(self, service: Type['Service'], method: MethodDescriptor, name: str):
        return method.prepare(service, name)

    def register(self, venom: 'venom.Venom') -> None:
        pass


class ServiceMeta(type):
    def __new__(metacls, what, bases=(), members=None):
        meta_, meta_changes = meta(bases, members)
        meta_ = meta_.manager.prepare_meta(what, meta_, meta_changes)
        manager = meta_.manager(meta_, meta_changes)
        method_descriptors = {}

        for base in bases:
            if isinstance(base, ServiceMeta):
                method_descriptors.update(base.__method_descriptors__)

        for name, member in members.items():
            if isinstance(member, MethodDescriptor):
                method_descriptors[name] = member

        stub = meta_changes.get('stub')
        if stub:
            if not isinstance(stub, type) and issubclass(stub, Service):
                raise TypeError('Meta.stub must be a Service')

        members['__manager__'] = manager
        members['__meta__'] = manager.meta
        members['__method_descriptors__'] = method_descriptors
        members['__stub__'] = stub
        cls = super(ServiceMeta, metacls).__new__(metacls, name, bases, members)

        if stub:
            for name, method in stub.__method_descriptors__.items():
                if name not in method_descriptors:
                    method_descriptors[name] = method

        cls.__methods__ = methods = {
            name: manager.prepare_method(cls, method, name)
            for name, method in method_descriptors.items()
        }

        for name, method in methods.items():
            setattr(cls, name, method)

        return cls


class Service(object, metaclass=ServiceMeta):
    """
    A service is a collection of functions, possibly HTTP routes.
    """
    __meta__: ClassVar['venom.util.AttributeDict'] = None
    __manager__: ClassVar[ServiceManager] = None
    __method_descriptors__: ClassVar[Dict[str, MethodDescriptor]] = None
    __methods__: ClassVar[Dict[str, Method]] = None
    __stub__: ClassVar[Type['Service']] = None

    context = RequestContextDescriptor()

    def __init__(self, venom: 'venom.rpc.Venom' = None) -> None:
        self.venom = venom

    class Meta:
        name = None
        manager = ServiceManager
        messages = ()
        converters = (
            StringValueConverter,
            IntegerValueConverter,
            NumberValueConverter,
            BoolValueConverter,
            DateTimeConverter,
            DateConverter)
        stub = None
        http_path = None

    def __repr__(self):
        return f'<Service [{self.__meta__.name}]>'
