from functools import partial

import asyncio
from threading import Thread
from typing import Type

from venom.rpc.comms import BaseClient
from venom.serialization import WireFormat, JSON

try:
    from grpc.beta import implementations
    from grpc.framework.interfaces.face import utilities
except ImportError:
    raise RuntimeError("You must install the 'grpcio' package to use the GRPC features of Venom RPC")


# TODO WARNING: GRPC Core is not asynchronous (as of October 2016). Therefore all calls made to the server are blocking.

def create_server(venom: 'venom.rpc.Venom',
                  *,
                  wire_format: Type[WireFormat] = None,
                  pool=None,
                  pool_size=None,
                  default_timeout=None,
                  maximum_timeout=None,
                  loop=None):
    if loop is None:
        loop = asyncio.new_event_loop()

    if wire_format is None:
        wire_format = JSON

    request_deserializers = {}
    response_serializers = {}
    method_implementations = {}

    def grpc_unary_unary(rpc, venom, service, request, context, *, loop):
        instance = venom.get_instance(service)
        future = asyncio.run_coroutine_threadsafe(rpc.invoke(instance, request), loop)
        # TODO use context.timeout
        return future.result()

    for service, rpc in venom.iter_methods():
        grpc_name = (service.__meta__.name, rpc.name)
        request_deserializers[grpc_name] = wire_format(rpc.request).unpack
        response_serializers[grpc_name] = wire_format(rpc.response).pack
        method_implementations[grpc_name] = utilities.unary_unary_inline(partial(grpc_unary_unary,
                                                                                 rpc,
                                                                                 venom,
                                                                                 service,
                                                                                 loop=loop))

    server_options = implementations.server_options(request_deserializers=request_deserializers,
                                                    response_serializers=response_serializers,
                                                    thread_pool=pool, thread_pool_size=pool_size,
                                                    default_timeout=default_timeout,
                                                    maximum_timeout=maximum_timeout)

    def event_loop_runner(loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    t = Thread(target=event_loop_runner, args=(loop,))
    t.daemon = True
    t.start()

    return implementations.server(method_implementations, options=server_options)


class Client(BaseClient):
    def __init__(self, stub: Type['venom.rpc.Service'], host=None, port=50051, *, wire_format: WireFormat = None):
        super().__init__(stub, wire_format=wire_format)
        channel = implementations.insecure_channel(host, port)
        self._group = stub.__meta__.name
        self._grpc_stub = self._create_grpc_stub(stub, channel)

    def _create_grpc_stub(self, stub, channel, host=None, metadata_transformer=None, pool=None, pool_size=None):
        request_serializers = {}
        response_deserializers = {}

        for rpc in stub.__methods__.values():
            request_serializers[(self._group, rpc.name)] = self._wire_format(rpc.request).pack
            response_deserializers[(self._group, rpc.name)] = self._wire_format(rpc.response).unpack

        stub_options = implementations.stub_options(host=host,
                                                    metadata_transformer=metadata_transformer,
                                                    request_serializers=request_serializers,
                                                    response_deserializers=response_deserializers,
                                                    thread_pool=pool,
                                                    thread_pool_size=pool_size)

        return implementations.generic_stub(channel, stub_options)

    async def invoke(self,
                     rpc: 'venom.stub.RPC',
                     request: 'venom.message.Message',
                     *,
                     context: 'venom.rpc.RequestContext' = None,
                     loop: asyncio.BaseEventLoop = None,
                     timeout: int = None):
        if loop is None:
            loop = asyncio.get_event_loop()

        future = loop.run_in_executor(None, partial(self._grpc_stub.blocking_unary_unary,
                                                    self._group,
                                                    rpc.name,
                                                    request,
                                                    timeout=timeout))

        return await future
