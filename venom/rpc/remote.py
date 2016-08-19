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

    async def invoke_(self, function, request):
        return await self._client.invoke(self._venom, self._context, function, request)

    class Meta:
        auto = False  # TODO functions & messages from schema


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