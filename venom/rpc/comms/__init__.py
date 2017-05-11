from abc import abstractmethod, ABC

from typing import Type, Generic, TypeVar, ClassVar

from venom.protocol import Protocol, JSONProtocol
from venom.rpc.method import Method, Req, Res

S = TypeVar('S', bound='venom.rcp.service.Service')


class ClientMethod(Method[S, Req, Res]):
    def __init__(self, client: 'AbstractClient[S]', stub_method: Method[S, Req, Res]):
        super().__init__(stub_method.name,
                         stub_method.request,
                         stub_method.response,
                         service=stub_method.service,
                         http_path=stub_method.http_path,
                         http_method=stub_method.http_method,
                         http_status=stub_method.http_status,
                         **stub_method.options)
        self.client = client

    async def invoke(self, instance, request: Req, loop: 'asyncio.AbstractEventLoop' = None) -> Res:
        return await self.client.invoke(self, request, loop=loop)


class AbstractClient(ABC, Generic[S]):
    client_method_cls: ClassVar[Type['ClientMethod']] = ClientMethod
    stub: S

    def __init__(self, stub: S, *, protocol_factory: Type[Protocol] = None):
        self.stub = stub
        # NOTE method bindings for all methods in the stub.
        for name, stub_method in stub.__methods__.items():
            method = self.client_method_cls(self, stub_method)
            # self.__methods__[name] = method
            setattr(self, name, method.__get__(stub))

        if protocol_factory is None:
            protocol_factory = JSONProtocol

        self._protocol_factory = protocol_factory

    @abstractmethod
    async def invoke(self, method: Method, request: 'venom.message.Message', *,
                     loop: 'asyncio.AbstractEventLoop' = None):
        raise NotImplementedError
