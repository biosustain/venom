import enum
import re
import types
from asyncio import iscoroutine, Future
from functools import wraps
from typing import Sequence, Callable, Any

from venom.message import Message, Empty
from venom.utils import AttributeDict

_RULE_PARAMETER_RE = re.compile('\{([^}]+)\}')


class BaseMethod(object):
    def __init__(self,
                 request: type(Message) = None,
                 response: type(Message) = None,
                 *,
                 name: str = None,
                 **options):
        self.request = request
        self.response = response
        self.name = name
        self.options = AttributeDict(options)


class Method(BaseMethod):
    def __init__(self, fn: Callable, **kwargs):
        super().__init__(**kwargs)
        self._fn = fn

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            return types.MethodType(self._fn, instance)

    def __set__(self, instance, value):
        raise AttributeError

    def as_view(self, venom: 'venom.rpc.Venom', service: type):
        fn = self._fn

        # TODO stream requests/responses
        @wraps(fn)
        async def view(request: type(Message)):
            instance = venom.get_instance(service)

            # TODO handle Empty message
            if type(request) == Empty:
                response = fn(instance)
            else:
                response = fn(instance, request)

            if iscoroutine(response) or isinstance(response, Future):
                response = await response

            return response
        return view


class MagicMethod(Method):
    """
    A method implementation that does not require a callable with (request) -> response format. Request messages are
    automatically generated or decomposed into keyword arguments.
    """
    pass  # TODO


class HTTPMethod(enum.Enum):
    GET = 'GET'
    PUT = 'PUT'
    POST = 'POST'
    PATCH = 'PATCH'
    DELETE = 'DELETE'


# TODO rpc and rpc.GET, POST... decorators

def rpc(*args, **kwargs):
    if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
        return Method(args[0])
    else:
        return lambda fn: Method(fn, *args, **kwargs)


# class Route(Method):
#     GET = None  # type: Callable[Any, Route]
#     PUT = None  # type: Callable[Any, Route]
#     POST = None  # type: Callable[Any, Route]
#     PATCH = None  # type: Callable[Any, Route]
#     DELETE = None  # type: Callable[Any, Route]
#
#     def __init__(self,
#                  method: HTTPMethod,
#                  fn,
#                  rule: str = None,
#                  relation: str = None,
#                  *,
#                  response_status: int = 200,
#                  **kwargs):
#         super().__init__(fn, **kwargs)
#         self._rule = rule
#         self._relation = relation
#         self.http_method = method
#         self.http_response_status = response_status
#
#     @property
#     def rule_parameter_names(self) -> Sequence[str]:
#         if self._rule is None:
#             return []
#         return [m.group(1) for m in re.finditer(_RULE_PARAMETER_RE, self._rule)]
#
#     # @property
#     # def request_parameter_locations(self):
#     #     pass
#
#
# def _route_decorator(method):
#     @classmethod
#     def decorator(cls, *args, **kwargs):
#         if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
#             return cls(method, args[0])
#         else:
#             return lambda f: cls(method, f, *args, **kwargs)
#
#     decorator.__name__ = method.name
#     return decorator
#
# for _method in HTTPMethod:
#     setattr(Route, _method.name, _route_decorator(_method))
