import inspect
from typing import Dict, no_type_check
from typing import Optional
from typing import Set
from typing import Type

from venom.common import IntegerValueConverter, BooleanValueConverter
from venom.common import StringValueConverter, NumberValueConverter
from venom.rpc.method import Method
from venom.message import Message
from venom.util import meta


class ServiceMeta(type):
    @staticmethod
    def _create_service_name(cls_name):
        name = cls_name.lower()
        for postfix in ('service', 'remote', 'stub'):
            if name.endswith(postfix):
                return name[:-len(postfix)]
        return name

    def __new__(mcs, name, bases, members):
        cls = super(ServiceMeta, mcs).__new__(mcs, name, bases, members)
        cls.__methods__ = methods = {}  # TODO change to tuple, but still prevent multiple methods with same name.
        cls.__messages__ = messages = set()
        cls.__meta__, meta_changes = meta(bases, members)

        for n, m in inspect.getmembers(cls):
            if n.startswith('__'):
                continue
            if isinstance(m, Method):
                m = methods[m.name or n] = m.register(cls, m.name or n)
                setattr(cls, n, m)  # TODO more elegant solution (first update members and then make cls)
            elif isinstance(m, type) and issubclass(m, Message):
                messages.add(m)

        if meta_changes.get('stub', None):
            for n, m in meta_changes['stub'].__methods__.items():
                if n not in cls.__methods__:
                    cls.__methods__[n] = m.register(cls, n)

        if not meta_changes.get('name', None):
            cls.__meta__.name = mcs._create_service_name(name)

        return cls


class Service(object, metaclass=ServiceMeta):
    """

    A service is a collection of functions, possibly HTTP routes.

    """
    __meta__ = None  # type: 'venom.util.AttributeDict'
    __methods__ = None  # type: Dict[str, Method]
    __messages__ = None  # type: Set[Type[Message]]

    def __init__(self, venom: 'venom.Venom' = None, context: 'venom.RequestContext' = None) -> None:
        self._venom = venom
        self._context = context

    class Meta:
        name = None
        messages = ()
        converters = (
            StringValueConverter,
            IntegerValueConverter,
            NumberValueConverter,
            BooleanValueConverter)
        stub = None
