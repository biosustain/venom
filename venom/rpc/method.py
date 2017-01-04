import asyncio
import enum
import re
from types import MethodType
from typing import Callable, Any, Type, Union, Set, Dict, Sequence, Tuple

from venom.converter import Converter
from venom.exceptions import NotImplemented_
from venom.message import Message, Empty
from venom.rpc.inspection import magic_normalize
from venom.rpc.resolver import Resolver
from venom.util import AttributeDict


_RULE_PARAMETER_RE = re.compile('\{([^}:]+)(:[^}]*)?\}')


class HTTPFieldLocation(enum.Enum):
    HEADER = 'header'
    QUERY = 'query'
    PATH = 'path'
    BODY = 'body'


class Method(object):
    def __init__(self,
                 request: Type[Message] = None,
                 response: Type[Message] = None,
                 *,
                 name: str = None,
                 http_verb: 'HTTPVerb' = None,
                 http_rule: str = None,
                 http_status: int = None,
                 **options) -> None:
        self.request = request
        self.response = response
        self.name = name
        self._http_rule = http_rule
        self._http_verb = http_verb
        self._http_status = http_status
        self.options = AttributeDict(options)

    def register(self, service: Type['venom.rpc.service.Service'], name: str) -> 'Method':
        """
        A hook that allows returning a customized :class:`Method` instance. For instance, the service definition may
        be used to fill in the blanks on what the `request` and `response` attributes should be.

        :param type service:
        :param str name:
        :return:
        """
        if self.name is None:
            self.name = name
        return self

    # TODO Error handling. Only errors that are venom.exceptions.Error instances should be raised
    async def invoke(self,
                     instance: 'venom.rpc.service.Service',
                     request: Message,
                     loop: 'asyncio.BaseEventLoop' = None) -> Message:
        raise NotImplementedError

    @property
    def http_verb(self) -> 'HTTPVerb':
        if self._http_verb is None:
            return HTTPVerb.POST
        return self._http_verb

    @property
    def http_status(self) -> int:
        if self._http_status is None:
            if self.response == Empty:
                return 204  # No Content
            return 200  # OK
        return self._http_status

    def http_rule(self, service: 'venom.Service' = None) -> str:
        if self._http_rule is None:
            http_rule = '/' + self.name.lower().replace('_', '-')
        else:
            http_rule = self._http_rule

        if service is not None:
            return service.__meta__.http_rule + http_rule
        return http_rule

    def http_path_params(self) -> Set[str]:
        return set(m.group(1) for m in re.finditer(_RULE_PARAMETER_RE, self._http_rule or ''))

    def http_field_locations(self) -> Dict[HTTPFieldLocation, Set[str]]:
        locations = {location: set() for location in HTTPFieldLocation}

        path = set()
        for name in self.http_path_params():
            if name in self.request.__fields__.keys():
                path.add(name)

        if path:
            locations[HTTPFieldLocation.PATH] = path

        remaining = set()
        for name in self.request.__fields__.keys():
            if name not in path:
                remaining.add(name)

        if self.http_verb in (HTTPVerb.POST, HTTPVerb.PATCH, HTTPVerb.PUT):
            locations[HTTPFieldLocation.BODY] = remaining
        else:
            locations[HTTPFieldLocation.QUERY] = remaining
        return locations


# TODO change return value to typing.Coroutine in Python 3.6
ServiceMethodInvokable = Callable[['venom.rpc.service.Service', Message], Message]


class ServiceMethod(Method):
    def __init__(self,
                 fn: Callable[..., Any],
                 request: Type[Message] = None,
                 response: Type[Message] = None,
                 name: str = None,
                 invokable: ServiceMethodInvokable = None,
                 **kwargs) -> None:
        super(ServiceMethod, self).__init__(request, response, name=name, **kwargs)
        self._fn = fn
        if invokable:
            self._invokable = invokable
        else:
            self._invokable = fn

    # NOTE: typing does not understand descriptors yet. There will be (inaccurate) warnings because the IDE
    #       cannot resolve this.
    def __get__(self, instance, owner) -> Union[Method, MethodType]:
        if instance is None:
            return self
        else:
            return MethodType(self._fn, instance)

    def __set__(self, instance, value):
        raise AttributeError

    def _register_stub(self, stub: Type['venom.rpc.service.Service'] = None) -> None:
        if stub:
            try:
                stub_method = stub.__methods__[self.name]
                self.request = self.request or stub_method.request
                self.response = self.response or stub_method.response
            except KeyError:
                pass  # method not specified in stub

    def register(self,
                 service: Type['venom.rpc.service.Service'],
                 name: str,
                 *args: Tuple[Resolver, ...],
                 converters: Sequence[Converter] = ()):
        # TODO Use Python 3.6 __set_name__()
        if self.name is None:
            self.name = name

        self._register_stub(service.__meta__.get('stub', None))

        magic_fn = magic_normalize(self._fn,
                                   request=self.request,
                                   response=self.response,
                                   additional_args=args,
                                   converters=tuple(converters) + tuple(service.__meta__.converters))

        return self.__class__(self._fn,
                              request=magic_fn.request,
                              response=magic_fn.response,
                              name=name,
                              invokable=magic_fn.invokable,
                              http_rule=self._http_rule,
                              http_verb=self._http_verb,
                              http_status=self._http_status,
                              **self.options)

    async def invoke(self,
                     instance: 'venom.service.Service',
                     request: Message,
                     loop: 'asyncio.BaseEventLoop' = None):
        try:
            return await self._invokable(instance, request, loop=loop)
        except NotImplementedError:
            raise NotImplemented_()
        return response


def rpc(*args, method_cls=ServiceMethod, **kwargs):
    if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
        return method_cls(args[0])
    else:
        return lambda fn: method_cls(fn, *args, **kwargs)


class HTTPVerb(enum.Enum):
    GET = 'GET'
    PUT = 'PUT'
    POST = 'POST'
    PATCH = 'PATCH'
    DELETE = 'DELETE'


def http(verb: HTTPVerb, rule=None, *args, **kwargs):
    return rpc(*args, http_verb=verb, http_rule=rule, **kwargs)


def http_method_decorator(verb, method_cls=ServiceMethod):
    def decorator(*args, method_cls=method_cls, **kwargs):
        if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
            return method_cls(args[0], http_verb=verb)
        else:
            return http(verb, *args, method_cls=method_cls, **kwargs)

    decorator.__name__ = verb.value
    return decorator


for _verb in HTTPVerb:
    setattr(http, _verb.name, http_method_decorator(_verb))
