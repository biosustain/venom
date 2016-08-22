from typing import Callable

import aiohttp

from venom.rpc import Remote
from venom.rpc.comms import BaseClient
from venom.rpc.method import BaseMethod, HTTPMethod, UnaryUnaryView
from venom.serialization import WireFormat, JSON

try:
    from aiohttp import web, ClientSession
except ImportError:
    raise RuntimeError("You must install the 'aiohttp' package to use this part of Venom")


def _route_handler(rpc: BaseMethod,
                   view: UnaryUnaryView,
                   wire_format: WireFormat):
    rpc_request = rpc.request
    rpc_response = rpc.response
    http_success = rpc.http_success
    http_rule_params = rpc.http_rule_params()
    http_request_body = rpc.http_request_body()

    async def handler(http_request):
        request = rpc_request()

        for param in http_rule_params:
            # TODO proper validation & assignment
            request[param] = http_request.match_info[param]

        if http_request_body:
            request.update(wire_format.unpack(http_request_body, await http_request.read()))

        # TODO error handling
        response = await view(request)

        return web.Response(body=wire_format.pack(rpc_response, response),
                            content_type=wire_format.mime,
                            status=http_success)

    return handler


def create_app(venom: 'venom.rpc.Venom',
               app: web.Application = None,
               wire_format: WireFormat = None,
               *,
               loop=None):
    if app is None:
        app = web.Application(loop=loop)

    if wire_format is None:
        wire_format = JSON()

    for service, rpc in venom.iter_methods():
        http_rule = '/' + service.__meta__.name.lower() + rpc.http_rule()

        view = rpc.as_view(venom, service)
        app.router.add_route(rpc.http_method.value, http_rule, _route_handler(rpc, view, wire_format))

    return app


class Client(BaseClient):
    def __init__(self,
                 remote: Remote,
                 base_url: str,
                 *,
                 wire_format: WireFormat = None,
                 **session_kwargs):
        super().__init__(remote, wire_format=wire_format)
        self._base_url = base_url
        self._session = aiohttp.ClientSession(**session_kwargs)

    async def invoke(self,
                     rpc: 'venom.remote.RPC',
                     request: 'venom.message.Message',
                     *,
                     context: 'venom.RequestContext' = None,
                     loop: 'asyncio.BaseEventLoop' = None,
                     timeout: int = None):

        with self._session as session:
            url = self._base_url + '/' + self._remote.__meta__.name.lower()

            if rpc.http_rule_params():
                url += rpc.http_rule().format(**request)
            else:
                url += rpc.http_rule()

            headers = None
            if rpc.http_method in (HTTPMethod.POST, HTTPMethod.PUT, HTTPMethod.PATCH):
                headers = {'content-type': self._wire_format.mime}

            body = self._wire_format.pack(rpc.http_request_body(), request)

            response = await session.request(rpc.http_method.value.lower(), url, headers=headers, data=body)

            if 200 <= response.status < 400:
                return self._wire_format.unpack(rpc.response, await response.read())
            else:
                pass
                # TODO error handling
