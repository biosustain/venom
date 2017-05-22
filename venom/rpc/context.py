import asyncio
from weakref import WeakKeyDictionary

from typing import Optional, MutableMapping

from venom.rpc.resolver import Resolver


class RequestContext(object):
    __contexts: MutableMapping[asyncio.Task, 'RequestContext'] = WeakKeyDictionary()
    _context_task: asyncio.Task = None

    def __init__(self):
        pass

    @classmethod
    def current(cls) -> Optional['RequestContext']:
        current_task = asyncio.Task.current_task()
        if current_task is None:
            return None
        return cls.__contexts.get(current_task)

    def __enter__(self) -> 'RequestContext':
        current_task = asyncio.Task.current_task()

        if current_task is None:
            raise RuntimeError('Unable to create RequestContext: No current task')

        if self._context_task is not None:
            raise RuntimeError('Unable to re-enter RequestContext: This context has already been entered')

        self._context_task = current_task
        self.__contexts[current_task] = self
        return self

    def __exit__(self, *args) -> None:
        del self.__contexts[self._context_task]


class RequestContextResolver(Resolver):
    python = RequestContext

    async def resolve(self,
                      service: 'venom.rpc.service.Service',
                      request: 'venom.message.Message') -> RequestContext:
        return service.context


class RequestContextDescriptor(object):
    def __get__(self, instance, owner) -> Optional['RequestContext']:
        return RequestContext.current()


class DictRequestContext(RequestContext, dict):
    def __hash__(self):
        return hash(self._context_task)
