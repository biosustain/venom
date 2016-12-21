import inspect
from typing import Dict, no_type_check, Any, Tuple
from typing import Optional
from typing import Set
from typing import Type

from venom.common import IntegerValueConverter, BooleanValueConverter, DateTimeConverter, DateConverter
from venom.common import StringValueConverter, NumberValueConverter
from venom.rpc.method import Method
from venom.message import Message
from venom.util import meta, MetaDict


class ServiceManager(object):
    def __init__(self, service: Type['Service'], meta: MetaDict, meta_changes: MetaDict):
        self.service = service

    @staticmethod
    def generate_service_name(cls_name: str) -> str:
        name = cls_name.lower()
        for postfix in ('service', 'remote', 'stub'):
            if name.endswith(postfix):
                return name[:-len(postfix)]
        return name

    @classmethod
    def prepare_meta(cls, meta: MetaDict, meta_changes: MetaDict) -> MetaDict:
        if not meta_changes.get('http_rule', None):
            meta.http_rule = '/' + meta.name.lower().replace('_', '-')
        return meta

    def register_method(self, method: Method, name: str) -> Method:
        return method.register(self.service, method.name or name)


class ServiceMeta(type):
    def __new__(metacls, name, bases, members):
        cls = super(ServiceMeta, metacls).__new__(metacls, name, bases, members)
        cls.__methods__ = methods = {}  # TODO change to tuple, but still prevent multiple methods with same name.
        cls.__messages__ = messages = set()

        meta_, meta_changes = meta(bases, members)

        if not meta_changes.get('name', None):
            meta_.name = meta_changes.name = meta_.manager.generate_service_name(name)

        cls.__meta__ = meta_.manager.prepare_meta(meta_, meta_changes)
        cls.__manager__ = manager = cls.__meta__.manager(cls, cls.__meta__, meta_changes)

        for n, m in inspect.getmembers(cls):
            if n.startswith('__'):
                continue
            if isinstance(m, Method):
                m = methods[m.name or n] = manager.register_method(m, n)
                setattr(cls, n, m)  # TODO more elegant solution (first update members and then make cls)
            elif isinstance(m, type) and issubclass(m, Message):
                messages.add(m)

        if meta_changes.get('stub', None):
            for n, m in meta_changes['stub'].__methods__.items():
                if n not in cls.__methods__:
                    cls.__methods__[n] = manager.register_method(m, n)

        return cls


class Service(object, metaclass=ServiceMeta):
    """

    A service is a collection of functions, possibly HTTP routes.

    """
    # TODO Python 3.6 ClassVar
    __meta__ = None  # type: 'venom.util.AttributeDict'
    __manager__ = None  # type: ServiceManager
    __methods__ = None  # type: Dict[str, Method]
    __messages__ = None  # type: Set[Type[Message]]

    def __init__(self, venom: 'venom.Venom' = None, context: 'venom.RequestContext' = None) -> None:
        self.venom = venom
        self.context = context

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
