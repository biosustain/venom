from functools import partial
from typing import Dict, Sequence, re

from venom.rpc.method import BaseMethod, HTTPMethod
from venom.rpc.service import Service


class Remote(Service):
    def __init__(self,
                 client: 'venom.comms.BaseClient',
                 venom: 'venom.Venom' = None,
                 context: 'venom.Context' = None):
        super().__init__(venom, context)
        self._client = client

    async def invoke_(self, rpc, request):
        return await self._client.invoke(self._venom, self._context, rpc, request)

    class Meta:
        auto = False  # TODO RPCs & messages from schema


class RPC(BaseMethod):
    # TODO async=False argument for synchronous use.

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            return partial(self._invoke_rpc, instance)

    def __set__(self, instance, value):
        raise AttributeError

    async def _invoke_rpc(self, remote: Remote, message_=None, **params):
        request = None

        if message_:
            request = message_
        elif len(params):
            assert self.request is not None
            request = self.request(**params)

        return await remote.invoke_(self, request)

    @staticmethod
    def http(method: HTTPMethod, rule=None, *args, **kwargs):
        return RPC(*args, http_method=method, http_rule=rule, **kwargs)

        # TODO consider changing RPC.http for better code suggestion:
        # class http:
        #     def __new__(cls, method: HTTPMethod, rule=None, *args, **kwargs):
        #         return RPC(*args, http_method=method, http_rule=rule, **kwargs)
        #
        #     POST = _http_rpc_decorator(HTTPMethod.POST)


def _http_rpc_decorator(http_method):
    def decorator(rule, *args, **kwargs):
        return RPC.http(http_method, rule, *args, **kwargs)

    decorator.__name__ = http_method.value
    return decorator


for _method in HTTPMethod:
    setattr(RPC.http, _method.name, _http_rpc_decorator(_method))


    # class RemoteRoute(RPC):
    #     def __init__(self,
    #                  method: HTTPMethod,
    #                  rule: str,
    #                  *args,
    #                  **kwargs):
    #         super().__init__(*args, **kwargs)
    #         self._rule = rule
    #         self.http_method = method
    #
    #     @property
    #     def rule(self):
    #         return self._rule
    #
    #     @property
    #     def rule_parameter_names(self) -> Sequence[str]:
    #         if self._rule is None:
    #             return []
    #         return [m.group(1) for m in re.finditer(_RULE_PARAMETER_RE, self._rule)]
