import inspect
from typing import Union, Any

from venom.rpc.method import BaseMethod
from venom.message import Message
from venom.utils import meta


class ServiceMeta(type):
    @staticmethod
    def _create_service_name(cls_name):
        name = cls_name.lower()
        for postfix in ('service', 'remote'):
            if name.endswith(postfix):
                return name[:-len(postfix)]
        return name

    def __new__(mcs, name, bases, members):
        cls = super(ServiceMeta, mcs).__new__(mcs, name, bases, members)  # type: Service
        cls.__methods__ = methods = {}  # TODO change to tuple, but still prevent multiple methods with same name.
        cls.__messages__ = messages = set()
        cls.__meta__, meta_changes = meta(bases, members)

        for n, m in inspect.getmembers(cls):
            if isinstance(m, BaseMethod):
                if m.name is None:
                    m.name = n
                methods[m.name] = m
            elif isinstance(m, type) and issubclass(m, Message):
                messages.add(m)

        if not meta_changes.get('name', None):
            cls.__meta__.name = mcs._create_service_name(name)

        return cls


class Service(object, metaclass=ServiceMeta):
    """

    A service is a collection of functions, possibly HTTP routes.

    """
    __meta__ = None
    __methods__ = None
    __messages__ = None

    def __init__(self, venom: 'venom.Venom' = None, context: 'venom.Context' = None):
        self._venom = venom
        self._context = context

    class Meta:
        name = None
        messages = ()


# TODO support services implementing a remote interface:
# class HelloService(Service):
#     class Meta:
#         remote = HelloRemote
#
#     def say_hello(self, request: HelloRequest) -> HelloResponse:
#         pass
