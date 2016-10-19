from typing import Type, Union, Iterable, Tuple
from weakref import WeakKeyDictionary

from venom.rpc.stub import Stub, RPC
from venom.serialization import WireFormat
from .service import Service
from .method import rpc, http


class UnknownService(RuntimeError):
    pass


class RequestContext(object):
    pass


class Venom(object):
    def __init__(self, *, wire_format: WireFormat = None):
        self._instances = WeakKeyDictionary()
        self._services = {}
        self._clients = {}

    # TODO change signature so that all keyword arguments go to the client_cls on init.
    # TODO add internal: bool = None flag; internal = False makes Stubs publicly available.
    def add(self,
            service: Type[Service],
            client: Type['venom.rpc.comms.Client'] = None,
            *client_args,
            **client_kwargs) -> None:

        name = service.__meta__.name
        if name in self._services:
            if self._services[name] is service:
                return
            raise ValueError("A service with name '{}' already exists".format(name))
        self._services[name] = service

        if client:
            self._clients[service] = client(service, *client_args, **client_kwargs)

    def _resolve_service_cls(self, reference: Union[str, type(Service)]):
        if isinstance(reference, str):
            try:
                return self._services[reference]
            except KeyError:
                raise UnknownService("No service with name '{}' is known to this Venom".format(reference))
        elif reference not in self._services.values():
            raise UnknownService("'{}' is not known to this Venom".format(reference))
        return reference

    def get_instance(self, reference: Union[str, type], context: RequestContext = None):
        cls = self._resolve_service_cls(reference)

        if context:
            try:
                return self._instances[context][cls]
            except KeyError:
                pass
        else:
            context = RequestContext()

        if issubclass(cls, Stub):
            instance = cls(self._clients[cls], venom=self, context=context)
        else:
            instance = cls(venom=self, context=context)

        if context:
            if context in self._instances:
                self._instances[context][cls] = instance
            else:
                self._instances[context] = {cls: instance}
        return instance

    def iter_methods(self) -> Iterable[Tuple[Type[Service], 'venom.rpc.method.Method']]:
        for service in self._services.values():
            # TODO add() to flag services as internal or external so that stubs can still be forwarded if wanted.
            if isinstance(service, Stub):
                continue

            for rpc in service.__methods__.values():
                yield service, rpc

    def __iter__(self) -> Iterable[Type[Service]]:
        return iter(self._services.values())
