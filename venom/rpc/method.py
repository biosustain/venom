import enum
import re
import types
from asyncio import iscoroutine, Future
from collections import OrderedDict
from functools import partial
from functools import wraps
from typing import Sequence, Callable, Any, Optional

from venom.message import Message, Empty, message_factory
from venom.utils import AttributeDict, upper_camelcase

_RULE_PARAMETER_RE = re.compile('\{([^}]+)\}')

# FIXME: is an Awaitable, not Callable
UnaryUnaryView = Callable[[Message], Message]


class BaseMethod(object):
    def __init__(self,
                 request: type(Message),
                 response: type(Message),
                 *,
                 name: str = None,
                 http_method: 'HTTPMethod' = None,
                 http_rule: str = None,
                 http_status: int = 200,
                 **options):
        """


        :param request:
        :param response:
        :param name:
        :param http_method:
        :param str http_rule: either `''` or a string beginning with `'/'` representing the route
        :param http_status:
        :param options:
        """
        self.request = request
        self.response = response
        self.name = name
        self._http_rule = http_rule
        self._http_method = http_method
        self.http_success = http_status
        self.options = AttributeDict(options)

    def http_rule(self):
        if self._http_rule is None:
            return '/' + self.name.lower().replace('_', '-')
        return self._http_rule

    def http_rule_params(self) -> Sequence[str]:
        return tuple(m.group(1) for m in re.finditer(_RULE_PARAMETER_RE, self.http_rule()))

    @property
    def http_method(self):
        if self._http_method is None:
            return HTTPMethod.POST
        return self._http_method

    # TODO cache result
    def http_request_body(self) -> Optional[type(Message)]:
        if self.http_method not in (HTTPMethod.POST, HTTPMethod.PATCH, HTTPMethod.PUT):
            return None

        http_rule_params = self.http_rule_params()

        if not http_rule_params:
            # TODO also return request if http_rule_params are not used in the request message for some reason
            return self.request

        return message_factory(upper_camelcase(self.name) + 'RequestBody', OrderedDict((
            (name, field) for name, field in self.request.__fields__.items()
            if name not in http_rule_params
        )))


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

    def as_view(self, venom: 'venom.rpc.Venom', service: type) -> UnaryUnaryView:
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


def http(method: HTTPMethod, rule=None, **kwargs):
    return rpc(http_method=method, http_rule=rule, **kwargs)


def _http_method_decorator(http_method):
    def decorator(*args, **kwargs):
        if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
            return Method(args[0], http_method=http_method)
        else:
            return http(http_method, *args, **kwargs)

    decorator.__name__ = http_method.value
    return decorator


for _method in HTTPMethod:
    setattr(http, _method.name, _http_method_decorator(_method))


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
