import asyncio
import enum
import re
import warnings
from functools import partial
from types import MethodType
from typing import Callable, Any, Type, Union, Set, Dict, Sequence, Tuple, Mapping, Optional, Awaitable, NamedTuple

from venom.converter import Converter
from venom.exceptions import NotImplemented_
from venom.message import Message, Empty, field_names
from venom.rpc.inspection import magic_normalize
from venom.rpc.resolver import Resolver
from venom.util import AttributeDict, MetaDict

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

    def prepare(self, manager: 'venom.rpc.service.ServiceManager', name: str) -> 'Method':
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
            http_rule = './' + self.name.lower().replace('_', '-')
        elif self._http_rule == '':
            http_rule = '.'
        else:
            http_rule = self._http_rule

        if service is not None and http_rule.startswith('.'):
            return service.__meta__.http_rule + http_rule[1:]
        return http_rule

    def http_path_params(self) -> Set[str]:
        return set(m.group(1) for m in re.finditer(_RULE_PARAMETER_RE, self._http_rule or ''))

    def http_field_locations(self) -> Dict[HTTPFieldLocation, Set[str]]:
        locations = {location: set() for location in HTTPFieldLocation}

        path = set()
        for name in self.http_path_params():
            if name in field_names(self.request):
                path.add(name)

        if path:
            locations[HTTPFieldLocation.PATH] = path

        remaining = set()
        for name in field_names(self.request):
            if name not in path:
                remaining.add(name)

        if self.http_verb in (HTTPVerb.POST, HTTPVerb.PATCH, HTTPVerb.PUT):
            locations[HTTPFieldLocation.BODY] = remaining
        else:
            locations[HTTPFieldLocation.QUERY] = remaining
        return locations


ServiceMethodInvokable = Callable[['venom.rpc.service.Service', Message], Awaitable[Message]]


class ServiceMethod(Method):
    def __init__(self,
                 fn: Callable[..., Any],
                 request: Type[Message] = None,
                 response: Type[Message] = None,
                 *,
                 name: str = None,
                 invokable: ServiceMethodInvokable = None,
                 **options) -> None:
        super(ServiceMethod, self).__init__(request, response, name=name, **options)
        self._fn = fn
        if invokable:
            self._invokable = invokable
            self._fn = invokable
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

    def prepare(self,
                manager: 'venom.rpc.service.ServiceManager',
                name: str,
                *args: Tuple[Resolver, ...],
                converters: Sequence[Converter] = ()):
        # TODO Use Python 3.6 __set_name__()

        if self.name is None:
            self.name = name

        self._register_stub(manager.meta.get('stub'))

        magic_fn = magic_normalize(func=self._fn,
                                   func_name=name,
                                   request=self.request,
                                   response=self.response,
                                   additional_args=args,
                                   converters=tuple(converters) + tuple(manager.meta.converters),
                                   auto_generate_request=self.options.get('auto', False))

        return ServiceMethod(self._fn,
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


class MethodDecorator(object):
    def __init__(self, method=ServiceMethod, **method_options):
        self.method = method
        self.method_options = method_options

    def __call__(self, *args, **kwargs) -> Union[Method, Callable[[Callable], Method]]:
        if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
            return self.method(args[0])
        else:
            return lambda fn: self.method(fn, *args, **kwargs)


rpc = MethodDecorator()


class HTTPVerb(enum.Enum):
    GET = 'GET'
    PUT = 'PUT'
    POST = 'POST'
    PATCH = 'PATCH'
    DELETE = 'DELETE'


class HTTPMethodDecorator(MethodDecorator):
    def __call__(self, verb: HTTPVerb, *args, **kwargs) -> Union[Method, Callable[[Callable], Method]]:
        if isinstance(verb, str):
            verb = HTTPVerb[verb]

        if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
            return self.method(args[0], http_verb=verb, **self.method_options)
        else:
            def _http(rule=None, *args, **kwargs):
                return MethodDecorator.__call__(self,
                                                *args,
                                                http_verb=verb,
                                                http_rule=rule,
                                                **kwargs,
                                                **self.method_options)

            return _http(*args, **kwargs)

    def GET(self, *args, **kwargs) -> Union[Method, Callable[[Callable], Method]]:
        warnings.warn("http.<HTTPVerb> is depreacated. Use http(<HTTPVerb>)", DeprecationWarning)
        return self(HTTPVerb.GET, *args, **kwargs)

    def PUT(self, *args, **kwargs) -> Union[Method, Callable[[Callable], Method]]:
        warnings.warn("http.<HTTPVerb> is depreacated. Use http(<HTTPVerb>)", DeprecationWarning)
        return self(HTTPVerb.PUT, *args, **kwargs)

    def POST(self, *args, **kwargs) -> Union[Method, Callable[[Callable], Method]]:
        warnings.warn("http.<HTTPVerb> is depreacated. Use http(<HTTPVerb>)", DeprecationWarning)
        return self(HTTPVerb.POST, *args, **kwargs)

    def PATCH(self, *args, **kwargs) -> Union[Method, Callable[[Callable], Method]]:
        warnings.warn("http.<HTTPVerb> is depreacated. Use http(<HTTPVerb>)", DeprecationWarning)
        return self(HTTPVerb.PATCH, *args, **kwargs)

    def DELETE(self, *args, **kwargs) -> Union[Method, Callable[[Callable], Method]]:
        warnings.warn("http.<HTTPVerb> is depreacated. Use http(<HTTPVerb>)", DeprecationWarning)
        return self(HTTPVerb.DELETE, *args, **kwargs)


http = HTTPMethodDecorator()
