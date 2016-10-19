import asyncio
import unittest
from functools import wraps
from typing import Union, Type, Iterable
from unittest.mock import MagicMock
from weakref import WeakKeyDictionary
from venom.rpc import Venom, UnknownService, Service, RequestContext
from venom.rpc.comms import BaseClient


class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)


class MockVenom(Venom):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._context_mock_instances = WeakKeyDictionary()

    def get_service(self, reference: Union[str, type], context: RequestContext = None):
        if context is not None:
            try:
                return self._context_mock_instances[context][reference]
            except KeyError:
                pass

        try:
            return super().get_instance(reference, context)
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


def mock_service(service: Type[Service], *dependencies: Iterable[Type[Service]], **kwargs):
    venom = mock_venom(service, *dependencies, **kwargs)
    return venom.get_instance(service, RequestContext())


def sync(coro):
    loop = asyncio.new_event_loop()
    future = loop.create_task(coro)
    loop.run_until_complete(future)
    return future.result()


def sync_decorator(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        return sync(fn(*args, **kwargs))

    return wrapper


class TestCaseMeta(type):
    def __new__(mcs, name, bases, members):
        for key, value in members.items():
            if key.startswith('test_') and asyncio.iscoroutinefunction(value):
                members[key] = sync_decorator(value)

        return super(TestCaseMeta, mcs).__new__(mcs, name, bases, members)


class AioTestCase(unittest.TestCase, metaclass=TestCaseMeta):
    """
    A custom unittest.TestCase that converts all tests that are coroutine functions into synchronous tests.
    """
    pass


class MockClient(MagicMock, BaseClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.responses = MagicMock()

    async def invoke(self, stub, rpc, request):
        return getattr(self.responses, rpc.name)(request)
