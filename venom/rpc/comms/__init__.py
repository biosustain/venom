from abc import abstractmethod, ABCMeta
from typing import Type

from venom.protocol import Protocol, JSON


class BaseClient(metaclass=ABCMeta):
    def __init__(self, stub: Type['venom.rpc.Service'], *, protocol_factory: Type[Protocol] = None):
        self._stub = stub

        if protocol_factory is None:
            protocol_factory = JSON

        self._protocol_factory = protocol_factory

    @abstractmethod
    async def invoke(self,
                     stub: 'venom.rpc.Service',
                     rpc: 'venom.rpc.stub.RPC',
                     request: 'venom.message.Message'):
        raise NotImplementedError
