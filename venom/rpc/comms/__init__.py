from abc import abstractmethod, ABCMeta

from venom.serialization import WireFormat, JSON


class BaseClient(metaclass=ABCMeta):

    def __init__(self, remote: 'venom.rpc.remote.Remote', *, wire_format: WireFormat = None):
        if wire_format is None:
            wire_format = JSON()

        self._wire_format = wire_format
        self._remote = remote

    @abstractmethod
    async def invoke(self,
                     rpc: 'venom.remote.RPC',
                     request: 'venom.message.Message',
                     *,
                     context: 'venom.RequestContext' = None,
                     loop: 'asyncio.BaseEventLoop' = None,
                     timeout: int = None):
        pass


class BaseServer(object):

    def __init__(self, *, loop=None, wire_format: WireFormat = None):
        if wire_format is None:
            wire_format = JSON()

        self._wire_format = wire_format
        self._loop = loop

