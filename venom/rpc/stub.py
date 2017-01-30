from types import MethodType
from typing import Union

from venom.exceptions import NotImplemented_
from venom.rpc.method import Method, HTTPVerb
from venom.rpc.service import Service


class Stub(Service):
    def __init__(self,
                 client: 'venom.comms.BaseClient' = None,
                 venom: 'venom.Venom' = None,
                 context: 'venom.RequestContext' = None):
        super().__init__(venom, context)
        self._client = client

    async def invoke_(self, rpc, request, loop: 'asyncio.BaseEventLoop' = None):
        if self._client:
            return await self._client.invoke(self, rpc, request, loop=loop, context=self.context)
        raise NotImplementedError


class RPC(Method):
    # NOTE: typing does not understand descriptors yet. There will be (inaccurate) warnings because the IDE
    #       cannot resolve this.
    def __get__(self, instance, owner) -> MethodType:
        if instance is None:
            return self
        else:
            return MethodType(self._invoke, instance)

    def __set__(self, instance, value):
        raise AttributeError

    async def _invoke(self,
                      service: 'venom.rpc.service.Service',
                      request: 'venom.Message',
                      loop: 'asyncio.BaseEventLoop' = None) -> 'venom.Message':
        if isinstance(service, Stub):
            return await service.invoke_(self, request, loop=loop)
        raise NotImplementedError

    async def invoke(self,
                     service: 'venom.rpc.service.Service',
                     request: 'venom.Message',
                     loop: 'asyncio.BaseEventLoop' = None) -> 'venom.Message':
        try:
            return await self._invoke(service, request, loop=loop)
        except NotImplementedError:
            raise NotImplemented_()

    @staticmethod
    def http(verb: Union[str, HTTPVerb], rule=None, *args, **kwargs) -> 'RPC':
        if isinstance(verb, str):
            verb = HTTPVerb[verb]
        return RPC(*args, http_verb=verb, http_rule=rule, **kwargs)
        # TODO consider changing RPC.http for better code suggestion:
        # class http:
        #     def __new__(cls, method: HTTPMethod, rule=None, *args, **kwargs):
        #         return RPC(*args, http_method=method, http_rule=rule, **kwargs)
        #
        #     POST = _http_rpc_decorator(HTTPMethod.POST)


def _http_rpc_decorator(verb):
    def decorator(rule, *args, **kwargs):
        return RPC.http(verb, rule, *args, **kwargs)

    decorator.__name__ = verb.value
    return decorator


for _verb in HTTPVerb:
    setattr(RPC.http, _verb.name, _http_rpc_decorator(_verb))