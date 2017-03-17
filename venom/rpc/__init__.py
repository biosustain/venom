from typing import Type, Union, Iterable, Tuple, ClassVar
from weakref import WeakKeyDictionary

import asyncio
from blinker import Signal

from venom.rpc.context import RequestContext, DictRequestContext
from venom.rpc.stub import Stub, RPC
from venom.protocol import Protocol
from .method import rpc, http
from .proxy import ServiceProxy
from .service import Service


class UnknownService(RuntimeError):
    pass


class Venom(object):
    on_add_service: ClassVar[Signal] = Signal('add-service')
    on_add_public_service: ClassVar[Signal] = Signal('add-public-service')
    before_invoke: ClassVar[Signal] = Signal('before-invoke')

    _request_context_cls: Type[RequestContext]

    def __init__(self, *, request_context_cls: Type[RequestContext] = DictRequestContext):
        self._request_context_cls = request_context_cls
        self._instances = WeakKeyDictionary()
        self._services = {}
        self._public_services = {}
        self._clients = {}

    # TODO change signature so that all keyword arguments go to the client_cls on init.
    # TODO add internal: bool = None flag; internal = False makes Stubs publicly available.
    def add(self,
            service: Type[Service],
            client: Type['venom.rpc.comms.HTTPClient'] = None,
            *client_args,
            public: bool = None,
            **client_kwargs) -> None:

        name = service.__meta__.name
        if name in self._services:
            if self._services[name] is service:
                return
            raise ValueError("A service with name '{}' already exists".format(name))

        self._services[name] = service

        if client:
            self._clients[service] = client(service, *client_args, **client_kwargs)
        elif public is None:
            public = True

        service.__manager__.register(self)
        self.on_add_service.send(self, service=service)

        if public:
            self._public_services[name] = service
            self.on_add_public_service.send(self, service=service)

    def _resolve_service_cls(self, reference: Union[str, Type[Service]]):
        if isinstance(reference, str):
            try:
                return self._services[reference]
            except KeyError:
                raise UnknownService("No service with name '{}' is known to this Venom".format(reference))
        elif reference not in self._services.values():
            raise UnknownService("'{}' is not known to this Venom".format(reference))
        return reference

    def get_instance(self, reference: Union[str, type]):
        cls = self._resolve_service_cls(reference)
        context = RequestContext.current()

        try:
            return self._instances[context][cls]
        except KeyError:
            pass

        if issubclass(cls, Stub):
            instance = cls(self._clients[cls], venom=self)
        else:
            instance = cls(venom=self)

        if context:
            if context in self._instances:
                self._instances[context][cls] = instance
            else:
                self._instances[context] = {cls: instance}
        return instance

    def iter_methods(self) -> Iterable[Tuple[Type[Service], 'venom.rpc.method.Method']]:
        for service in self._public_services.values():
            for rpc in service.__methods__.values():
                yield service, rpc

    def get_request_context(self) -> RequestContext:
        return self._request_context_cls(self)

    async def _invoke(self,
                      service: Type[Service],
                      method: 'venom.rpc.method.Method',
                      request: 'venom.Message'):
        with self._request_context_cls(self):
            instance = self.get_instance(service)
            self.before_invoke.send(self, service=service, method=method, request=request)
            return await method.invoke(instance, request)

    async def invoke(self,
                     service: Type[Service],
                     method: 'venom.rpc.method.Method',
                     request: 'venom.Message',
                     loop: 'asyncio.AbstractEventLoop' = None):
        if loop is None:
            loop = asyncio.get_event_loop()
        return await loop.create_task(self._invoke(service, method, request))

    def __iter__(self) -> Iterable[Type[Service]]:
        return iter(self._public_services.values())

