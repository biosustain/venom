from abc import abstractmethod, ABCMeta

from typing import TypeVar, Generic, Type

T = TypeVar('_T')


class Resolver(Generic[T], metaclass=ABCMeta):
    python: Type[T] = None

    async def __call__(self,
                       service: 'venom.rpc.service.Service',
                       request: 'venom.message.Message') -> T:
        return await self.resolve(service, request)

    @abstractmethod
    async def resolve(self,
                      service: 'venom.rpc.service.Service',
                      request: 'venom.message.Message') -> T:
        pass
