import asyncio

import aiohttp
from aiohttp.web_request import BaseRequest
from typing import Type

from venom.common import FieldMask
from venom.exceptions import Error, ErrorResponse
from venom.protocol import JSONProtocol, Protocol, URIStringProtocol, URIStringDictMessageTranscoder
from venom.rpc import RequestContext
from venom.rpc.comms import AbstractClient
from venom.rpc.method import Method, HTTPVerb, HTTPFieldLocation

try:
    from aiohttp import web, ClientSession
except ImportError:
    raise RuntimeError("You must install the 'aiohttp' package to use the AioHTTP features of Venom RPC")


class AioHTTPRequestContext(RequestContext):
    request: BaseRequest

    def __init__(self, request: BaseRequest):
        self.request = request


def _route_handler(venom: 'venom.rpc.Venom', method: Method, protocol_factory: Type[Protocol]):
    rpc_response = protocol_factory(method.response)
    rpc_error_response = protocol_factory(ErrorResponse)

    http_status = method.http_status

    http_field_locations = method.http_field_locations()

    http_request_body = JSONProtocol(method.request, FieldMask(http_field_locations[HTTPFieldLocation.BODY]))

    http_request_query = URIStringDictMessageTranscoder(URIStringProtocol,
                                                        method.request,
                                                        FieldMask(http_field_locations[HTTPFieldLocation.QUERY]))

    http_request_path = URIStringDictMessageTranscoder(URIStringProtocol,
                                                       method.request,
                                                       FieldMask(http_field_locations[HTTPFieldLocation.PATH]))

    async def handler(http_request):
        try:
            request = http_request_body.unpack(await http_request.read())
            http_request_query.decode(http_request.url.query, request)
            http_request_path.decode(http_request.match_info, request)

            response = await venom.invoke(method, request, context=AioHTTPRequestContext(http_request))
            return web.Response(body=rpc_response.pack(response),
                                content_type=rpc_response.mime,
                                status=http_status)
        except Error as e:
            return web.Response(body=rpc_error_response.pack(e.format()),
                                content_type=rpc_error_response.mime,
                                status=e.http_status)

    return handler


def _path_field_template(field, default):
    if not field.repeated and field.type == int:
        return f'{field.json_name}:\d+'
    return default


def create_app(venom: 'venom.rpc.Venom',
               app: web.Application = None,
               protocol_factory: Type[Protocol] = JSONProtocol):
    if app is None:
        app = web.Application()

    for method in venom.iter_methods():
        app.router.add_route(method.http_method.value,
                             method.format_http_path(json_names=True, field_template_hook=_path_field_template),
                             _route_handler(venom, method, protocol_factory))

    return app


class HTTPClient(AbstractClient):
    def __init__(self,
                 stub: Type['venom.rpc.Service'],
                 base_url: str,
                 *,
                 protocol_factory: Type[Protocol] = None,
                 session: aiohttp.ClientSession = None,
                 **session_kwargs):
        super().__init__(stub, protocol_factory=protocol_factory)
        self._base_url = base_url

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

        params = URIStringDictMessageTranscoder(
            URIStringProtocol,
            method.request,
            FieldMask(http_field_locations[HTTPFieldLocation.QUERY])).encode(request)

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
