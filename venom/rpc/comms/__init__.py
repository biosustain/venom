from abc import abstractmethod, ABCMeta
from typing import Type

from venom.serialization import WireFormat, JSON


class BaseClient(metaclass=ABCMeta):
    def __init__(self, stub: Type['venom.rpc.Service'], *, wire_format: WireFormat = None):
        self._stub = stub

        if wire_format is None:
            wire_format = JSON

        self._wire_format = wire_format

    @abstractmethod
    async def invoke(self,
                     stub: 'venom.rpc.Service',
                     rpc: 'venom.rpc.stub.RPC',
                     request: 'venom.message.Message'):
        raise NotImplementedError
