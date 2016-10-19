from asyncio import iscoroutine, Future
from typing import Type, Any

import aiohttp
from aiohttp import web

from venom.exceptions import Error, ErrorResponse, ValidationError, NotImplemented_
from venom.fields import Field, ConverterField
from venom.rpc import Stub
from venom.rpc.comms import BaseClient
from venom.rpc.method import Method, HTTPVerb
from venom.serialization import JSON, WireFormat


try:
    from aiohttp import web, ClientSession
except ImportError:
    raise RuntimeError("You must install the 'aiohttp' package to use the AioHTTP features of Venom RPC")


def _cast(type_: type, value: Any):
    # TODO JSON type names, i.e. object instead of dict, integer instead of int etc.
    try:
        return type_(value)
    except ValueError:
        raise ValidationError("{} is not formatted as a '{}'".format(repr(value), type_.__name__))


def _request_param_resolver(field: Field):
    if field.type in (int, str):
        return lambda value: _cast(field.type, value)
    raise NotImplementedError()
    # TODO other string conversions


def _route_handler(venom: 'venom.rpc.Venom',
                   service: Type['venom.rpc.Service'],
                   rpc: Method,
                   wire_format: Type[WireFormat]):
    rpc_request = wire_format(rpc.request)
    rpc_response = wire_format(rpc.response)
    rpc_error_response = wire_format(ErrorResponse)

    http_status = rpc.http_status
    http_rule_params = [(name, _request_param_resolver(rpc.request.__fields__[name]))
                        for name in rpc.http_rule_params()]
    http_request_body = rpc.http_verb in (HTTPVerb.POST, HTTPVerb.PATCH, HTTPVerb.PUT) or \
                        len(http_rule_params) == len(rpc.request.__fields__)

    async def handler(http_request):
        try:
            if http_request_body:
                request = rpc_request.unpack(await http_request.read(), skip=http_rule_params)
            else:
                request = rpc.request()

            for param, resolve in http_rule_params:
                # TODO catch for missing params
                request[param] = resolve(http_request.match_info[param])

            instance = venom.get_instance(service)
            response = rpc.invoke(instance, request)

            if iscoroutine(response) or isinstance(response, Future):
                response = await response

            return web.Response(body=rpc_response.pack(response),
                                content_type=rpc_response.mime,
                                status=http_status)
        except Error as e:
            return web.Response(body=rpc_error_response.pack(e.format()),
                                content_type=wire_format.mime,
                                status=e.http_status)
        except NotImplementedError:
            e = NotImplemented_()
            # FIXME errors should be produced by the Method.invoke() call itself!
            return web.Response(body=rpc_error_response.pack(e.format()),
                                content_type=wire_format.mime,
                                status=e.http_status)

        # TODO 500 error fallback, other error fallbacks
    return handler


def create_app(venom: 'venom.rpc.Venom',
               app: web.Application = None,
               wire_format: Type[WireFormat] = None,
               loop=None):
    if app is None:
        app = web.Application(loop=loop)

    if wire_format is None:
        wire_format = JSON

    for service, rpc in venom.iter_methods():
        http_rule = rpc.http_rule(service)
        app.router.add_route(rpc.http_verb.value, http_rule, _route_handler(venom, service, rpc, wire_format))

    return app


class Client(BaseClient):
    def __init__(self,
                 stub: Type['venom.rpc.Service'],
                 base_url: str,
                 *,
                 wire_format: WireFormat = None,
                 session: aiohttp.ClientSession = None,
                 **session_kwargs):
        super().__init__(stub, wire_format=wire_format)
        self._base_url = base_url
        if session is None:
            self._session = aiohttp.ClientSession(**session_kwargs)
        else:
            self._session = session

    async def invoke(self,
                     stub: 'venom.rpc.Service',
                     rpc: 'venom.rpc.stub.RPC',
                     request: 'venom.message.Message',
                     *,
                     context: 'venom.RequestContext' = None,
                     loop: 'asyncio.BaseEventLoop' = None,
                     timeout: int = None):

        # TODO optional timeouts

        if rpc.http_rule_params():
            url = self._base_url + rpc.http_rule(stub).format(**request)
        else:
            url = self._base_url + rpc.http_rule(stub)

        headers = None
        if rpc.http_verb in (HTTPVerb.POST, HTTPVerb.PUT, HTTPVerb.PATCH):
            headers = {'content-type': self._wire_format.mime}

        body = self._wire_format(rpc.request).pack(request)

        async with self._session.request(rpc.http_verb.value.lower(), url, headers=headers, data=body) as response:
            if 200 <= response.status < 400:
                return self._wire_format(rpc.response).unpack(await response.read())
            else:
                self._wire_format(ErrorResponse).unpack(await response.read()).raise_()

    # XXX not sure if session should be opened for each request, and why an unclosed session is such a bad thing.
    def __del__(self):
        if self._session:
            self._session.close()
