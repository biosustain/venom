import asyncio
import enum
import re
from abc import ABCMeta

from types import MethodType
from typing import Callable, Any, Type, Union, Set, Dict, Sequence, Tuple, Awaitable, TypeVar, Generic, overload

from venom.converter import Converter
from venom.exceptions import NotImplemented_
from venom.fields import Field, FieldDescriptor
from venom.message import Message, Empty, field_names
from venom.rpc.inspection import magic_normalize
from venom.rpc.resolver import Resolver
from venom.validation import MessageValidator

_RULE_PARAMETER_RE = re.compile('\{([^}:]+)(:[^}]*)?\}')


class HTTPFieldLocation(enum.Enum):
    HEADER = 'header'
    QUERY = 'query'
    PATH = 'path'
    BODY = 'body'


class HTTPVerb(enum.Enum):
    GET = 'GET'
    PUT = 'PUT'
    POST = 'POST'
    PATCH = 'PATCH'
    DELETE = 'DELETE'


Req = TypeVar('Req', bound=Message)
Res = TypeVar('Res', bound=Message)

Service = 'venom.rpc.service.Service'


class MethodDescriptor(Generic[Req, Res], metaclass=ABCMeta):
    def __init__(self,
                 request: Type[Req] = None,
                 response: Type[Res] = None,
                 name: Union[str, Callable[[Service], str]] = None,
                 *,
                 http_path: Union[str, Callable[[Service], str]] = None,
                 http_method: HTTPVerb = None,
                 http_status: int = None,
                 **options: Dict[str, Any]) -> None:
        self.request = request
        self.response = response
        self.name = name

        self.http_path = http_path
        self.http_method = http_method
        self.http_status = http_status
        self.options = options

        self._attr_name = None

    def __set_name__(self, owner: Any, name: str):
        self._attr_name = name

    @overload
    def __get__(self, instance: None, owner: Type[Service] = None) -> 'MethodDescriptor[Req, Res]':
        pass

    @overload
    def __get__(self, instance: Service, owner: Type[Service] = None) -> 'Callable[[Any, Req], Awaitable[Res]]':
        pass

    # XXX MethodDescriptor.__get__() is not used anymore
    def __get__(self, instance, owner):
        if self._attr_name:
            from .stub import Stub
            from .service import Service
            if issubclass(owner, Stub):
                method = self.stub(owner, self._attr_name)
                setattr(owner, self._attr_name, method)
            elif isinstance(instance, Service):
                method = self.prepare(instance, self._attr_name)
                setattr(instance, self._attr_name, method)
            else:
                return self
            if instance:
                return method.__get__(instance, owner)
            return method
        return self

    def _get_name(self, service: Type[Service], attr_name: str):
        if not self.name:
            return attr_name
        if callable(self.name):
            return self.name(service)
        return self.name

    def _get_http_path(self, service: Type[Service], name: str):
        if self.http_path is None:
            http_path = f"./{name.lower().replace('_', '-')}"
        elif callable(self.http_path):
            http_path = self.http_path(service)
        elif self.http_path == '':
            http_path = '.'
        else:
            http_path = self.http_path

        if service is not None and http_path.startswith('.'):
            return service.__meta__.http_path + http_path[1:]
        return http_path

    def _get_http_method(self) -> HTTPVerb:
        if self.http_method is None:
            return HTTPVerb.POST
        return self.http_method

    def _get_http_status(self, response: Type[Message]):
        if self.http_status is None:
            if response == Empty:
                return 204  # No Content
            return 200  # OK
        return self.http_status

    def prepare(self, service: Type[Service], attr_name: str) -> 'Method':
        name = self._get_name(service, attr_name)
        return Method(name,
                      self.request or Empty,
                      self.response or Empty,
                      service,
                      http_path=self._get_http_path(service, name),
                      http_method=self._get_http_method(),
                      http_status=self._get_http_status(self.response or Empty),
                      **self.options)

    def stub(self, stub: Type[Service], name: str) -> 'Method':
        return Method(self.name or name,
                      self.request or Empty,
                      self.response or Empty,
                      stub,
                      http_path=self._get_http_path(stub, self.name or name),
                      http_method=self._get_http_method(),
                      http_status=self._get_http_status(self.response or Empty),
                      **self.options)


S = TypeVar('S', bound='venom.rpc.service.Service')


class Method(Generic[S, Req, Res], MethodDescriptor[Req, Res]):
    service: Type[S]

    def __init__(self,
                 name: str,
                 request: Type[Req],
                 response: Type[Res],
                 service: Type[S],
                 *,
                 http_path: str,
                 http_method: HTTPVerb,
                 http_status: int,
                 **options: Dict[str, Any]) -> None:
        super().__init__(request,
                         response,
                         name,
                         http_path=http_path,
                         http_method=http_method,
                         http_status=http_status,
                         **options)
        self.service = service
        self._request_validator = MessageValidator(request)

    def format_http_path(self,
                         *,
                         json_names: bool = True,
                         field_template_hook: Callable[[FieldDescriptor, str], str] = None,
                         before_field_template: str = '{',
                         after_field_template: str = '}') -> str:
        parts = []
        for i, part in enumerate(re.split(r'{([^}]+)}', self.http_path)):
            if i % 2 == 1:  # every odd part is a path parameter
                field = self.request.__fields__[part]
                if json_names:
                    part = field.json_name
                if field_template_hook:
                    part = field_template_hook(field, part)
                parts.append(f'{before_field_template}{part}{after_field_template}')
            else:
                parts.append(part)

        return ''.join(parts)

    def http_path_parameters(self) -> Set[str]:
        return set(m.group(1) for m in re.finditer(_RULE_PARAMETER_RE, self.http_path or ''))

    def http_field_locations(self) -> Dict[HTTPFieldLocation, Set[str]]:
        locations = {location: set() for location in HTTPFieldLocation}

        path = set()
        for name in self.http_path_parameters():
            if name in field_names(self.request):
                path.add(name)

        if path:
            locations[HTTPFieldLocation.PATH] = path

        remaining = set()
        for name in field_names(self.request):
            if name not in path:
                remaining.add(name)

        if self.http_method in (HTTPVerb.POST, HTTPVerb.PATCH, HTTPVerb.PUT):
            locations[HTTPFieldLocation.BODY] = remaining
        else:
            locations[HTTPFieldLocation.QUERY] = remaining
        return locations

    def validate(self, request: Req):
        self._request_validator.validate(request)

    # TODO Error handling. Only errors that are venom.exceptions.Error instances should be raised
    async def invoke(self, instance: S, request: Req, loop: 'asyncio.AbstractEventLoop' = None) -> Res:
        raise NotImplemented_()

    @overload
    def __get__(self, instance: None, owner: Type[S] = None) -> 'MethodDescriptor[Req, Res]':
        pass

    @overload
    def __get__(self, instance: S, owner: Type[S] = None) -> 'Callable[[S, Req], Awaitable[Res]]':
        pass

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        else:
            return MethodType(self.invoke, instance)

    def __repr__(self):
        return f'<{self.__class__.__name__} [{self.service.__meta__.name}.{self.name}]>'
        # return f'<{self.__class__.__name__} ' \
        #        f'[{self.name}({self.request.__meta__.name}) -> {self.response.__meta__.name}]>'


class ServiceMethodDescriptor(MethodDescriptor[Req, Res]):
    def __init__(self,
                 func: Callable[..., Any],
                 request: Type[Req] = None,
                 response: Type[Res] = None,
                 name: Union[str, Callable[[Service], str]] = None,
                 *,
                 http_path: Union[str, Callable[[Service], str]] = None,
                 http_method: HTTPVerb = None,
                 http_status: int = None,
                 **options: Dict[str, Any]) -> None:
        super().__init__(request,
                         response,
                         name,
                         http_path=http_path,
                         http_method=http_method,
                         http_status=http_status,
                         **options)
        self._func = func

    def prepare(self,
                service: Type[Service],
                attr_name: str,
                *args: Tuple[Resolver, ...],
                converters: Sequence[Converter] = ()) -> 'ServiceMethod':
        name = self._get_name(service, attr_name)
        request = self.request
        response = self.response

        if service.__stub__:
            try:
                stub_method = service.__stub__.__methods__[name]
                request = request or stub_method.request
                response = response or stub_method.response

            except KeyError:
                pass  # method not specified in stub

        magic_func = magic_normalize(self._func,
                                     func_name=attr_name,
                                     request=request,
                                     response=response,
                                     owner=service,
                                     additional_args=args,
                                     converters=tuple(converters) + tuple(service.__meta__.converters),
                                     auto_generate_request=self.options.get('auto', False))

        return ServiceMethod(name,
                             magic_func.request,
                             magic_func.response,
                             service,
                             magic_func.invokable,
                             http_path=self._get_http_path(service, name),
                             http_method=self._get_http_method(),
                             http_status=self._get_http_status(magic_func.response),
                             **self.options)

    def stub(self, stub: Type[Service], name: str) -> 'Method':
        magic_func = magic_normalize(self._func,
                                     func_name=name,
                                     request=self.request,
                                     response=self.response,
                                     converters=tuple(stub.__meta__.converters),
                                     auto_generate_request=self.options.get('auto', False))

        return Method(name,
                      magic_func.request,
                      magic_func.response,
                      stub,
                      http_path=self._get_http_path(stub, name),
                      http_method=self._get_http_method(),
                      http_status=self._get_http_status(magic_func.response),
                      **self.options)

        # def __call__(self, *args, **kwargs):
        #     return self._func(*args, **kwargs)


class ServiceMethod(Method[S, Req, Res]):
    implementation: Callable[[S, Req], Awaitable[Res]]

    def __init__(self,
                 name: str,
                 request: Type[Req],
                 response: Type[Res],
                 service: Type[S],
                 implementation: Callable[[S, Req], Awaitable[Res]],
                 *,
                 http_path: str = None,
                 http_method: HTTPVerb = None,
                 http_status: int = None,
                 **options: Dict[str, Any]) -> None:
        super().__init__(name,
                         request,
                         response,
                         service,
                         http_path=http_path,
                         http_method=http_method,
                         http_status=http_status,
                         **options)
        self.implementation = implementation

    def prepare(self, service: Type[Service], attr: str) -> 'ServiceMethod':
        return ServiceMethod(attr,
                             self.request,
                             self.response,
                             service,
                             self.implementation,
                             http_path=self._get_http_path(service, attr),
                             http_method=self._get_http_method(),
                             http_status=self._get_http_status(self.response),
                             **self.options)

    async def invoke(self, instance: S, request: Message, loop: 'asyncio.AbstractEventLoop' = None):
        self.validate(request)

        try:
            return await self.implementation(instance, request, loop=loop)
        except NotImplementedError:
            raise NotImplemented_()


class MethodDecorator(object):
    def __init__(self, descriptor=ServiceMethodDescriptor, **method_options):
        self.descriptor = descriptor
        self.descriptor_kwargs = method_options

    def __call__(self, *args, **kwargs) -> Union[Method, Callable[[Callable], Method]]:
        if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
            return self.descriptor(args[0])
        else:
            return lambda fn: self.descriptor(fn, *args, **kwargs)


class HTTPMethodDecorator(MethodDecorator):
    def __call__(self, method: HTTPVerb, *args, **kwargs) -> Union[Method, Callable[[Callable], Method]]:
        if isinstance(method, str):
            verb = HTTPVerb[method]

        if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
            return self.descriptor(args[0], http_method=method, **self.descriptor_kwargs)
        else:
            def _http(path=None, *args, **kwargs):
                return MethodDecorator.__call__(self,
                                                *args,
                                                http_method=method,
                                                http_path=path,
                                                **kwargs,
                                                **self.descriptor_kwargs)

            return _http(*args, **kwargs)

    def GET(self, *args, **kwargs) -> Union[Method, Callable[[Callable], Method]]:
        return self(HTTPVerb.GET, *args, **kwargs)

    def PUT(self, *args, **kwargs) -> Union[Method, Callable[[Callable], Method]]:
        return self(HTTPVerb.PUT, *args, **kwargs)

    def POST(self, *args, **kwargs) -> Union[Method, Callable[[Callable], Method]]:
        return self(HTTPVerb.POST, *args, **kwargs)

    def PATCH(self, *args, **kwargs) -> Union[Method, Callable[[Callable], Method]]:
        return self(HTTPVerb.PATCH, *args, **kwargs)

    def DELETE(self, *args, **kwargs) -> Union[Method, Callable[[Callable], Method]]:
        return self(HTTPVerb.DELETE, *args, **kwargs)


rpc = MethodDecorator()
http = HTTPMethodDecorator()
