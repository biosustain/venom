import asyncio
from functools import wraps
from inspect import signature, Parameter
from typing import Callable, Any, Sequence, get_type_hints, Type, NamedTuple, Optional
from typing import Tuple
from typing import Union
from venom.fields import RepeatField, MapField

from venom.converter import Converter

from venom.message import Empty, Message, get_or_default
from venom.rpc.resolver import Resolver

MessageFunction = NamedTuple('MessageFunction', [
    ('request', Type[Message]),
    ('response', Type[Message]),
    ('invokable', Callable[[Any, Message, Optional['asyncio.BaseEventLoop']], Message])  # TODO update to typing.Coroutine in Python 3.6
])


# TODO name arg for use with auto-generation
def magic_normalize(func: Callable[..., Any],
                    request: Type[Message] = None,
                    response: Type[Message] = None,
                    converters: Sequence[Converter] = (),
                    # TODO replace with Sequence[Union[Converter, Type[Converter]]] see https://github.com/python/typing/issues/266
                    additional_args: Sequence[Resolver] = ()) -> MessageFunction:
    """

    :param func:
    :param request:
    :param response:
    :param converters:
    :param additional_args: additional arguments that are resolved during invocation.
    :return:
    """
    # TODO parameters supplied by the service implementation through a context; session etc.

    additional_args = [resolver() if isinstance(resolver, type) else resolver for resolver in additional_args]
    converters = [converter() if isinstance(converter, type) else converter for converter in converters]

    func_signature = signature(func)
    func_type_hints = get_type_hints(func)

    if len(func_signature.parameters) == 0:
        # no "self" parameter: func()
        raise RuntimeError("At least one argument expected in {}".format(func))

    request_converter = None
    func_parameters = tuple(func_signature.parameters.items())[1 + len(additional_args):]

    if len(func_parameters):
        name, param = func_parameters[0]
        type_ = func_type_hints.get(name, Any)

        unpack_request = False  # type: Union[bool, Tuple[str, ...]]

        if issubclass(type_, Message) and name == 'request':
            # func(self, request: MessageType, ...)
            if request is None:
                request = type_
            elif request != type_ and 'request' not in request.__fields__:
                raise RuntimeError("Bad argument in {}: "
                                   "'{}' should be {}, but got {}".format(func, name, request, type_))

            for name, param in func_parameters[1:]:
                if param.default is Parameter.empty:
                    raise RuntimeError("Unexpected required argument in {}: '{}'".format(func, name))
        elif request is not None and name == 'request':
            for converter in converters:
                if converter.wire == request and converter.python == type_:
                    request_converter = converter
                    break

            if not request_converter:
                raise RuntimeError("Unable to coerce request message to python format: "
                                   "'{}' in {}".format(type_, func))
        else:  # func(self, arg: ?, ...)
            required_params, remaining_params = {}, {}
            for name, param in func_parameters:

                if param.default is Parameter.empty:
                    required_params[name] = func_type_hints.get(name, Any)
                else:
                    remaining_params[name] = (func_type_hints.get(name, Any), param.default)

            if request:  # unpack from request message
                message_params = set()

                for name, type_ in required_params.items():
                    if name not in request.__fields__:
                        raise RuntimeError("Unexpected required argument in {}: "
                                           "'{}' is not a field of {}".format(func, name, request))

                    field_type = request.__fields__[name].type
                    if isinstance(request.__fields__[name], (RepeatField, MapField)):
                        # TODO support Dict[str, ?] and List[?] for RepeatField and MapField respectively.
                        raise NotImplementedError

                    if type_ not in (Any, request.__fields__[name].type):
                        raise RuntimeError("Bad argument in {}: "
                                           "'{}' should be {}, but got {}".format(func, name, field_type, type_))
                    message_params.add((name, None))

                for name, (type_, default) in remaining_params.items():
                    if name in request.__fields__:
                        field_type = request.__fields__[name].type

                        if isinstance(request.__fields__[name], (RepeatField, MapField)):
                            # TODO support Dict[str, ?] and List[?] for RepeatField and MapField respectively.
                            raise NotImplementedError

                        if type_ not in (Any, field_type):
                            raise RuntimeError("Bad argument in {}: "
                                               "'{}' should be {}, but got {}".format(func, name, field_type, type_))

                        message_params.add((name, default))

                if message_params == set(request.__fields__.keys()):
                    unpack_request = True
                else:
                    unpack_request = tuple(message_params)

            else:  # auto-generate message from params (uses converters where necessary)
                unpack_request = True
                raise NotImplementedError  # TODO
    else:  # func(self)
        if request is None:
            request = Empty

        # either request is Empty, or otherwise all request fields are discarded -- strange, but valid
        unpack_request = ()

    return_type = func_type_hints.get('return', Any)
    response_converter = None

    if response is None:
        if return_type in (Any, None):
            # TODO warn if Any: missing return type annotation (will discard return value)
            response = Empty
        elif issubclass(return_type, Message):
            response = return_type
        else:
            for converter in converters:
                if converter.python == return_type:
                    response_converter = converter
                    response = converter.wire
                    break

            if not response_converter:
                raise RuntimeError("Unable to coerce return value to wire format: "
                                   "'{}' in {}".format(return_type, func))
    elif return_type == Any:
        # NOTE missing return type annotation (assuming 'response' here)
        pass
    elif return_type is None:
        response = Empty
    elif response != return_type:
        for converter in converters:
            if converter.wire == response and converter.python == return_type:
                response_converter = converter
                break

        if not response_converter:
            raise RuntimeError("Unable to coerce return value to wire format: "
                               "'{}' in {}".format(return_type, func))

    wrap_args = lambda req: (req,)
    wrap_kwargs = lambda req: {}

    if unpack_request is True:
        wrap_args = lambda req: ()
        wrap_kwargs = lambda req: req
    elif unpack_request is False:
        if request_converter:
            wrap_args = lambda req: (request_converter.convert(req),)
    elif unpack_request == ():
        wrap_args = lambda req: ()
    else:
        wrap_args = lambda req: ()
        wrap_kwargs = lambda req: {f: req.get(f, d) for f, d in unpack_request}

    if response == Empty and return_type != Empty:
        wrap_response = lambda res: Empty()
    elif response_converter:
        wrap_response = lambda res: response_converter.format(res)
    else:
        wrap_response = lambda res: res

    if not asyncio.iscoroutinefunction(func):
        func_ = func

        @wraps(func)
        async def func(*args, **kwargs):
            return func_(*args, **kwargs)

    # TODO (optimization) do not wrap what does not need to be wrapped
    if additional_args:
        async def invokable(inst, req: Message, loop: 'asyncio.BaseEventLoop' = None) -> Message:
            return wrap_response(await func(inst,
                                            *(await asyncio.gather(*[arg.resolve(inst, req)
                                                                     for arg in additional_args], loop=loop)),
                                            *wrap_args(req),
                                            **wrap_kwargs(req)))
    else:
        async def invokable(inst, req: Message, loop: 'asyncio.BaseEventLoop' = None) -> Message:
            return wrap_response(await func(inst, *wrap_args(req), **wrap_kwargs(req)))

    return MessageFunction(request, response, wraps(func)(invokable))
