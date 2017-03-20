from typing import Dict, Any, MutableMapping

from venom.common import IntegerValueConverter, BooleanValueConverter, DateTimeConverter, DateConverter
from venom.common import StringValueConverter, NumberValueConverter
from venom.rpc.context import RequestContextDescriptor
from venom.rpc.method import Method
from venom.util import meta, MetaDict


class ServiceManager(object):
    def __init__(self, meta: MetaDict, meta_changes: MetaDict):
        self.meta = meta
        self.methods = {}

    @staticmethod
    def generate_service_name(cls_name: str) -> str:
        name = cls_name.lower()
        for postfix in ('service', 'remote', 'stub'):
            if name.endswith(postfix):
                return name[:-len(postfix)]
        return name

    @classmethod
    def prepare_meta(cls, name: str, meta: MetaDict, meta_changes: MetaDict) -> MetaDict:
        if not meta_changes.get('name'):
            meta.name = cls.generate_service_name(name)

        if not meta_changes.get('http_rule', None):
            meta.http_rule = '/' + meta.name.lower().replace('_', '-')
        return meta

    def prepare_members(self, members: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
        for name, member in members.items():
            if isinstance(member, Method):
                members[name] = method = self.prepare_method(member, name)
                self.methods[method.name] = method
        return members

    def prepare_method(self, method: Method, name: str) -> Method:
        return method.prepare(self, name)

    def register(self, venom: 'venom.Venom') -> None:
        pass


class ServiceMeta(type):
    def __new__(metacls, name, bases, members):
        meta_, meta_changes = meta(bases, members)
        meta_ = meta_.manager.prepare_meta(name, meta_, meta_changes)
        manager = meta_.manager(meta_, meta_changes)

        for base in bases:
            if isinstance(base, ServiceMeta):
                manager.methods.update(base.__methods__)

        stub = meta_changes.get('stub')
        if isinstance(stub, type) and issubclass(stub, Service):
            for name, method in stub.__methods__.items():
                manager.methods[method.name] = method

        cls = super(ServiceMeta, metacls).__new__(metacls, name, bases, manager.prepare_members(members))
        cls.__meta__ = manager.meta
        cls.__methods__ = manager.methods
        cls.__manager__ = manager
        return cls


class Service(object, metaclass=ServiceMeta):
    """

    A service is a collection of functions, possibly HTTP routes.

    """
    __meta__: 'venom.util.AttributeDict' = None
    __manager__: ServiceManager = None
    __methods__: Dict[str, Method] = None

    context = RequestContextDescriptor()

    def __init__(self, venom: 'venom.Venom' = None) -> None:
        self.venom = venom

    class Meta:
        name = None
        manager = ServiceManager
        messages = ()
        converters = (
            StringValueConverter,
            IntegerValueConverter,
            NumberValueConverter,
            BooleanValueConverter,
            DateTimeConverter,
            DateConverter)
        stub = None
        http_rule = None
