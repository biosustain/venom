import enum
import re
from types import MethodType
from typing import Callable, Any, Type, Union, Sequence, Set

from venom.message import Message
from venom.rpc.inspection import magic
from venom.util import AttributeDict


_RULE_PARAMETER_RE = re.compile('\{([^}:]+)(:[^}]*)?\}')


class Method(object):
    def __init__(self,
                 request: Type[Message] = None,
                 response: Type[Message] = None,
                 *,
                 name: str = None,
                 http_verb: 'HTTPVerb' = None,
                 http_rule: str = None,
                 http_status: int = 200,
                 **options) -> None:
        self.request = request
        self.response = response
        self.name = name
        self._http_rule = http_rule
        self._http_verb = http_verb
        self.http_status = http_status
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

    def invoke(self, instance: 'venom.rpc.service.Service', request: Message):
        raise NotImplementedError

    @property
    def http_verb(self) -> 'HTTPVerb':
        if self._http_verb is None:
            return HTTPVerb.POST
        return self._http_verb

    def http_rule(self, service: 'venom.Service') -> str:
        service_http_rule = '/' + service.__meta__.name.lower().replace('_', '-')
        if self._http_rule is None:
            return service_http_rule + '/' + self.name.lower().replace('_', '-')
        return service_http_rule + self._http_rule

    def http_rule_params(self) -> Set[str]:
        return set(m.group(1) for m in re.finditer(_RULE_PARAMETER_RE, self._http_rule or ''))


class ServiceMethod(Method):
    def __init__(self,
                 func: Callable[..., Any],
                 request: Type[Message] = None,
                 response: Type[Message] = None,
                 name: str = None,
                 invokable_func: Callable[['venom.rpc.service.Service', Message], Message] = None,
                 **kwargs) -> None:
        super(ServiceMethod, self).__init__(request, response, name=name, **kwargs)
        self._func = func
        if invokable_func:
            self._invokable_func = invokable_func
        else:
            self._invokable_func = func

    # NOTE: typing does not understand descriptors yet. There will be (inaccurate) warnings because the IDE
    #       cannot resolve this.
    def __get__(self, instance, owner) -> Union[Method, MethodType]:
        if instance is None:
            return self
        else:
            return MethodType(self._func, instance)

    def __set__(self, instance, value):
        raise AttributeError

    def register(self, service: 'venom.rpc.service.ServiceType', name: str):
        # TODO get request, response from stub.

        if self.name is None:
            self.name = name

        stub = service.__meta__.stub
        if stub:
            try:
                stub_method = stub.__methods__[name]
                self.request = self.request or stub_method.request
                self.response = self.response or stub_method.response
            except KeyError:
                pass  # method not specified in stub

        converters = [c() if isinstance(c, type) else c for c in service.__meta__.converters]
        magic_func = magic(self._func,
                           request=self.request,
                           response=self.response,
                           converters=converters)

        return self.__class__(self._func,
                              request=magic_func.request,
                              response=magic_func.response,
                              name=name,
                              invokable_func=magic_func.invokable,
                              http_rule=self._http_rule,
                              http_verb=self._http_verb,
                              http_status=self.http_status,
                              **self.options)

    def invoke(self, instance: 'venom.service.Service', request: Message):
        return self._invokable_func(instance, request)


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


def _http_method_decorator(verb):
    def decorator(*args, method_cls=ServiceMethod, **kwargs):
        if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
            return method_cls(args[0], http_verb=verb)
        else:
            return http(verb, *args, method_cls=method_cls, **kwargs)

    decorator.__name__ = verb.value
    return decorator


for _verb in HTTPVerb:
    setattr(http, _verb.name, _http_method_decorator(_verb))
