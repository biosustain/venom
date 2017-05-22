import asyncio

from blinker import Signal
from typing import Type, Union, Iterable, ClassVar, TypeVar, overload, Mapping

from venom.rpc.context import RequestContext, DictRequestContext
from venom.rpc.stub import Stub
from venom.validation import MessageValidator
from .method import rpc, http, Method
from .proxy import ServiceProxy, proxy
from .service import Service


class UnknownService(RuntimeError):
    pass


S = TypeVar('S', bound=Service)


class Venom(object):
    on_add_service: ClassVar[Signal] = Signal('add-service')
    on_add_public_service: ClassVar[Signal] = Signal('add-public-service')
    before_invoke: ClassVar[Signal] = Signal('before-invoke')

    _default_request_context_cls: Type[RequestContext]
    _instances: Mapping[Service, Union[Service, 'venom.rpc.comms.AbstractClient']]

    def __init__(self, *, default_request_context_cls: Type[RequestContext] = DictRequestContext, **options):
        self._default_request_context_cls = default_request_context_cls
        self._instances = {}
        self._services = {}
        self._public_services = {}
        self._clients = {}
        self.options = options

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
            raise ValueError(f"A service with name '{name}' already exists")

        self._services[name] = service

        if client:
            self._clients[service] = client(service(self), *client_args, **client_kwargs)
        elif public is None:
            public = True

        service.__manager__.register(self)

        if public:
            self._public_services[name] = service
            self._instances[service] = instance = service(self)
            self.on_add_public_service.send(self, service=instance)

    def _resolve_service_cls(self, reference: Union[str, Type[Service]]):
        if isinstance(reference, str):
            try:
                return self._services[reference]
            except KeyError:
                raise UnknownService(f"No service with name '{reference}' is known to this Venom")
        elif reference not in self._services.values():
            raise UnknownService("'{}' is not known to this Venom".format(reference))
        return reference

    @overload
    def get_instance(self, reference: Type[S]) -> S:
        pass

    @overload
    def get_instance(self, reference: str) -> Service:
        pass

    def get_instance(self, reference):
        cls = self._resolve_service_cls(reference)

        try:
            return self._instances[cls]
        except KeyError:
            pass

        if issubclass(cls, Stub):
            instance = self._clients[cls]
        else:
            raise RuntimeError
            # self._instances[cls] = instance = cls(venom=self)

        return instance

    def iter_methods(self) -> Iterable[Method]:
        for instance in self._instances.values():
            for method in instance.__methods__.values():
                yield method

    def get_request_context(self) -> RequestContext:
        return self._default_request_context_cls()

    async def _invoke(self, method: Method, request: 'venom.Message', context: RequestContext):
        with context:
            instance = self.get_instance(method.service)
            self.before_invoke.send(self, method=method, request=request)
            return await method.invoke(instance, request)

    async def invoke(self,
                     method: Method,
                     request: 'venom.Message',
                     *,
                     context: RequestContext = None,
                     loop: 'asyncio.AbstractEventLoop' = None):

        if context is None:
            context = self._default_request_context_cls()

        if loop is None:
            loop = asyncio.get_event_loop()
        return await loop.create_task(self._invoke(method, request, context))

    def __iter__(self) -> Iterable[Type[Service]]:
        return iter(self._instances.values())
