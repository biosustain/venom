from asyncio import Future
from functools import partial

import asyncio
from grpc.beta import implementations
from grpc.framework.interfaces.face import utilities

from venom.rpc import Remote
from venom.rpc.comms import BaseClient
from venom.serialization import WireFormat, JSON


def create_server(venom: 'venom.rpc.Venom',
                  *,
                  wire_format: WireFormat = None,
                  pool=None,
                  pool_size=None,
                  default_timeout=None,
                  maximum_timeout=None,
                  loop=None):

    if loop is None:
        loop = asyncio.get_event_loop()

    if wire_format is None:
        wire_format = JSON()

    request_deserializers = {}
    response_serializers = {}
    method_implementations = {}
    for service in venom:
        if isinstance(service, Remote):
            continue

        def grpc_unary_unary(view, request, context, *, loop):
            future = asyncio.ensure_future(view(request), loop=loop)
            loop.run_until_complete(future)
            return future.result()

        for rpc in service.__methods__.values():
            grpc_name = (service.__meta__.name, rpc.name)
            request_deserializers[grpc_name] = partial(wire_format.unpack, rpc.request)
            response_serializers[grpc_name] = partial(wire_format.pack, rpc.response)
            method_implementations[grpc_name] = utilities.unary_unary_inline(partial(grpc_unary_unary,
                                                                                     rpc.as_view(venom, service),
                                                                                     loop=loop))

    server_options = implementations.server_options(request_deserializers=request_deserializers,
                                                    response_serializers=response_serializers,
                                                    thread_pool=pool, thread_pool_size=pool_size,
                                                    default_timeout=default_timeout,
                                                    maximum_timeout=maximum_timeout)

    return implementations.server(method_implementations, options=server_options)


class Client(BaseClient):
    def __init__(self, remote, host=None, port=50051, *, wire_format: WireFormat = None):
        super().__init__(remote, wire_format=wire_format)
        channel = implementations.insecure_channel(host, port)
        self._group = self._remote.__meta__.name
        self._stub = self._create_stub(channel)

    def _create_stub(self, channel, host=None, metadata_transformer=None, pool=None, pool_size=None):
        request_serializers = {}
        response_deserializers = {}

        for rpc in self._remote.__methods__.values():
            # rpc.options.grpc_name = uppercamelcase(rpc.name)
            request_serializers[(self._group, rpc.name)] = partial(self._wire_format.pack, rpc.request)
            response_deserializers[(self._group, rpc.name)] = partial(self._wire_format.unpack, rpc.response)

        stub_options = implementations.stub_options(host=host,
                                                    metadata_transformer=metadata_transformer,
                                                    request_serializers=request_serializers,
                                                    response_deserializers=response_deserializers,
                                                    thread_pool=pool,
                                                    thread_pool_size=pool_size)

        return implementations.generic_stub(channel, stub_options)

    async def invoke(self,
                     rpc: 'venom.remote.RPC',
                     request: 'venom.message.Message',
                     *,
                     context: 'venom.RequestContext' = None,
                     loop: asyncio.BaseEventLoop = None,
                     timeout: int = None):
        if loop is None:
            loop = asyncio.get_event_loop()

        future = loop.run_in_executor(None, partial(self._stub.blocking_unary_unary,
                                                    self._group,
                                                    rpc.name,
                                                    request,
                                                    timeout=timeout))

        return await future
