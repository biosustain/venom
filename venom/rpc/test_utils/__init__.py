import asyncio
import unittest
from functools import wraps
from unittest.mock import MagicMock
from weakref import WeakKeyDictionary

from typing import Union, Type, Iterable

from venom.rpc import Venom, UnknownService, Service
from venom.rpc.context import RequestContext


class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)


class MockVenom(Venom):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._context_mock_instances = WeakKeyDictionary()

    def get_instance(self, reference: Union[str, type]):
        context = RequestContext.current()

        if context is not None:
            try:
                return self._context_mock_instances[context][reference]
            except KeyError:
                pass

        try:
            return super().get_instance(reference)
        except UnknownService:
            instance = AsyncMock()

        if context is not None:
            if context in self._context_mock_instances:
                self._context_mock_instances[context][reference] = instance
            else:
                self._context_mock_instances[context] = {reference: instance}

        return instance


def mock_venom(*services: Iterable[Type[Service]], **kwargs):
    venom = MockVenom(**kwargs)
    for service in services:
        venom.add(service)
    return venom


def mock_instance(service: Type[Service], *dependencies: Iterable[Type[Service]], **kwargs):
    venom = mock_venom(service, *dependencies, **kwargs)
    return venom.get_instance(service)


def sync(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    future = loop.create_task(coro)
    loop.run_until_complete(future)
    return future.result()


def sync_decorator(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        return sync(fn(*args, **kwargs))

    return wrapper


class AioTestCaseMeta(type):
    def __new__(mcs, name, bases, members):
        for key, value in members.items():
            if key.startswith('test_') and asyncio.iscoroutinefunction(value):
                members[key] = sync_decorator(value)

        return super(AioTestCaseMeta, mcs).__new__(mcs, name, bases, members)


class AioTestCase(unittest.TestCase, metaclass=AioTestCaseMeta):
    """
    A custom unittest.TestCase that converts all tests that are coroutine functions into synchronous tests.
    """
    pass
