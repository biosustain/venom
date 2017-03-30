from typing import Type

import aiohttp
import asyncio

from venom.exceptions import Error, ErrorResponse
from venom.rpc.comms import AbstractClient
from venom.rpc.method import Method, HTTPVerb, HTTPFieldLocation
from venom.protocol import JSON, Protocol, DictProtocol, URIString

try:
    from aiohttp import web, ClientSession
except ImportError:
    raise RuntimeError("You must install the 'aiohttp' package to use the AioHTTP features of Venom RPC")


def _route_handler(venom: 'venom.rpc.Venom',
                   method: Method,
                   protocol_factory: Type[Protocol],
                   query_protocol_factory: Type[DictProtocol] = URIString,
                   path_protocol_factory: Type[DictProtocol] = URIString):
    rpc_response = protocol_factory(method.response)
    rpc_error_response = protocol_factory(ErrorResponse)

    http_status = method.http_status

    http_field_locations = method.http_field_locations()
    http_request_body = protocol_factory(method.request, http_field_locations[HTTPFieldLocation.BODY])
    http_request_query = query_protocol_factory(method.request, http_field_locations[HTTPFieldLocation.QUERY])
    http_request_path = path_protocol_factory(method.request, http_field_locations[HTTPFieldLocation.PATH])

    async def handler(http_request):
        try:
            request = http_request_body.unpack(await http_request.read())
            http_request_query.decode(http_request.url.query, request)
            http_request_path.decode(http_request.match_info, request)

            response = await venom.invoke(method, request)
            return web.Response(body=rpc_response.pack(response),
                                content_type=rpc_response.mime,
                                status=http_status)
        except Error as e:
            return web.Response(body=rpc_error_response.pack(e.format()),
                                content_type=rpc_error_response.mime,
                                status=e.http_status)
    return handler


def create_app(venom: 'venom.rpc.Venom',
               app: web.Application = None,
               protocol_factory: Type[Protocol] = JSON):
    if app is None:
        app = web.Application()

    for method in venom.iter_methods():
        app.router.add_route(method.http_method.value,
                             method.http_path,
                             _route_handler(venom, method, protocol_factory))

    return app


class HTTPClient(AbstractClient):
    def __init__(self,
                 stub: Type['venom.rpc.Service'],
                 base_url: str,
                 *,
                 protocol_factory: Type[Protocol] = None,
                 query_protocol_factory: Type[DictProtocol] = URIString,
                 path_protocol_factory: Type[DictProtocol] = URIString,
                 session: aiohttp.ClientSession = None,
                 **session_kwargs):
        super().__init__(stub, protocol_factory=protocol_factory)
        self._base_url = base_url
        self._query_protocol_factory = query_protocol_factory
        self._path_protocol_factory = path_protocol_factory

        if session is None:
            self._session = aiohttp.ClientSession(**session_kwargs)
        else:
            self._session = session

    async def invoke(self,
                     method: Method,
                     request: 'venom.message.Message',
                     *,
                     context: 'venom.RequestContext' = None,
                     loop: 'asyncio.AbstractEventLoop' = None,
                     timeout: int = None):

        # TODO optional timeouts

        if method.http_path_parameters():
            url = self._base_url + method.http_path.format(**request)
        else:
            url = self._base_url + method.http_path

        headers = None
        if method.http_method in (HTTPVerb.POST, HTTPVerb.PUT, HTTPVerb.PATCH):
            headers = {'content-type': self._protocol_factory.mime}

        http_field_locations = method.http_field_locations()

        # TODO cache this for each RPC call in HTTPClient.__init__()
        params = self._query_protocol_factory(method.request,
                                              http_field_locations[HTTPFieldLocation.QUERY]).encode(request)
        body = self._protocol_factory(method.request,
                                      http_field_locations[HTTPFieldLocation.BODY]).pack(request)

        async with self._session.request(method.http_method.value.lower(), url,
                                         headers=headers,
                                         data=body,
                                         params=params) as response:
            if 200 <= response.status < 400:
                return self._protocol_factory(method.response).unpack(await response.read())
            else:
                self._protocol_factory(ErrorResponse).unpack(await response.read()).raise_()

    # XXX not sure if session should be opened for each request, and why an unclosed session is such a bad thing.
    def __del__(self):
        if self._session:
            self._session.close()


Client = HTTPClient
