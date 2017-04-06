import asyncio
from functools import wraps
from inspect import signature, Parameter
from typing import Callable, Any, Sequence, get_type_hints, Type, NamedTuple, Optional, List, Dict, TypeVar
from typing import Tuple
from typing import Union
from venom.fields import RepeatField, MapField, Field, ConverterField, Repeat

from venom.converter import Converter

from venom.message import Empty, Message, message_factory, fields, field_names
from venom.rpc.resolver import Resolver
from venom.util import upper_camelcase

MessageFunction = NamedTuple('MessageFunction', [
    ('request', Type[Message]),
    ('response', Type[Message]),
    ('invokable', Callable[[Any, Message, Optional['asyncio.AbstractEventLoop']], Message])  # TODO update to typing.Coroutine in Python 3.6
])


def get_field_type(field):
    # TODO support other mappings and sequences
    # XXX support for list-within-a-list situations?
    if isinstance(field, RepeatField):
        return List[field.items.type]
    elif isinstance(field, MapField):
        return Dict[str, field.values.type]
    elif isinstance(field, Field):
        return field.type
    else:
        raise NotImplementedError


def create_field_from_type(type_, converters: Sequence[Converter] = (), default: Any = None):
    if type_ in (bool, int, float, str, bytes):
        return Field(type_, default=default)

    for converter in converters:
        if converter.python == type_:
            return ConverterField(converter)

    # TODO type_ != Any is a workaround for https://github.com/python/typing/issues/345
    if type_ != Any and issubclass(type_, List):
        # FIXME List[List[X]] must not become Repeat(Repeat(X))
        return Repeat(create_field_from_type(type_.__args__[0]))

    # TODO type_ != Any is a workaround for https://github.com/python/typing/issues/345
    if type_ != Any and issubclass(type_, Message):
        return Field(type_)

    raise NotImplementedError(f"Unable to generate field for {type_}")


def dynamic(name: str, expression: Union[type, Callable[[Type[Any]], type]]) \
        -> Callable[[Callable[..., Any]], Callable[..., Any]]:  # TODO type annotations for pass-through decorator
    """
    
    :param name: 
    :param expression: a subclass of ``type`` or a callable in the format ``(owner: Type[Any]) -> type``.
    :return: 
    """
    def decorator(func):
        if not hasattr(func, '__dynamic__'):
            func.__dynamic__ = {name: expression}
        else:
            func.__dynamic__[name] = expression
        return func
    return decorator


def _get_func_type_annotations(func: Callable[..., Any], owner: type = None) -> Dict[str, type]:
    annotations = dict(get_type_hints(func))
    dynamic_annotations = getattr(func, '__dynamic__', {})

    for name, expression in dynamic_annotations.items():
        if type(expression) == type:
            annotations[name] = expression
        elif callable(expression):
            annotations[name] = expression(owner)
    return annotations


# TODO name arg for use with auto-generation
def magic_normalize(func: Callable[..., Any],
                    func_name: str = None,
                    request: Type[Message] = None,
                    response: Type[Message] = None,
                    *,
                    converters: Sequence[Union[Converter, Type[Converter]]] = (),
                    additional_args: Sequence[Union[Resolver, Type[Resolver]]] = (),
                    owner: type = None,
                    auto_generate_request: bool = False) -> MessageFunction:
    """

    :param func:
    :param request:
    :param response:
    :param converters:
    :param owner: 
    :param additional_args: additional arguments that are resolved during invocation.
    :return:
    """
    if func_name is None:
        func_name = func.__name__

    # TODO parameters supplied by the service implementation through a context; session etc.

    additional_args = [resolver() if isinstance(resolver, type) else resolver for resolver in additional_args]
    converters = [converter() if isinstance(converter, type) else converter for converter in converters]

    func_signature = signature(func)
    func_type_hints = _get_func_type_annotations(func, owner)


    if len(func_signature.parameters) == 0:
        # no "self" parameter: func()
        raise RuntimeError(f"At least one argument expected in {func}")

    request_converter = None
    func_parameters = tuple(func_signature.parameters.items())[1 + len(additional_args):]

    if len(func_parameters):
        name, param = func_parameters[0]
        param_type = func_type_hints.get(name, Any)

        unpack_request: Union[bool, Tuple[str, ...]] = False

        # TODO param_type != Any is a workaround for https://github.com/python/typing/issues/345
        if param_type != Any and issubclass(param_type, Message) and name == 'request':
            # func(self, request: MessageType, ...)
            if request is None:
                request = param_type
            elif request != param_type and 'request' not in field_names(request):
                raise RuntimeError(f"Bad argument in {func}: "
                                   f"'{name}' should be {request}, but got {param_type}")

            for name, param in func_parameters[1:]:
                if param.default is Parameter.empty:
                    raise RuntimeError(f"Unexpected required argument in {func}: '{name}'")
        elif request is not None and name == 'request':
            for converter in converters:
                if converter.wire == request and converter.python == param_type:
                    request_converter = converter
                    break

            if not request_converter:
                raise RuntimeError(f"Unable to coerce request message to python format: "
                                   f"'{param_type}' in {func}")
        else:  # func(self, arg: ?, ...)
            required_params, remaining_params = {}, {}
            for name, param in func_parameters:

                param_type = func_type_hints.get(name, Any)
                if hasattr(param_type, '__supertype__'):  # handles NewType
                    param_type = param_type.__supertype__

                if param.default is Parameter.empty:
                    required_params[name] = param_type
                else:
                    remaining_params[name] = (param_type, param.default)

            if request:  # unpack from request message
                request_fields = request.__fields__
                message_params = set()

                for name, param_type in required_params.items():
                    try:
                        field = request_fields[name]
                    except KeyError:
                        raise RuntimeError(f"Unexpected required argument in {func}: "
                                           f"'{name}' is not a field of {request}")

                    field_type = get_field_type(field)

                    if param_type not in (Any, field_type):
                        raise RuntimeError(f"Bad argument in {func}: "
                                           f"'{name}' should be {field_type}, but got {param_type}")

                    message_params.add((name, None))

                for name, (param_type, default) in remaining_params.items():
                    if name in request_fields:
                        field = request_fields[name]
                        field_type = get_field_type(field)

                        if param_type not in (Any, field_type):
                            raise RuntimeError(f"Bad argument in {func}: "
                                               f"'{name}' should be {field_type}, but got {param_type}")

                        message_params.add((name, default))

                if message_params == field_names(request):
                    unpack_request = True
                else:
                    unpack_request = tuple(message_params)

            else:  # auto-generate message from params (uses converters where necessary)
                unpack_request = True

                if not auto_generate_request:
                    raise RuntimeError(f"Message auto-generation required in {func}")

                message_fields = {}
                for name, param in func_parameters:
                    param_type = func_type_hints.get(name, Any)
                    if hasattr(param_type, '__supertype__'):  # handles NewType
                        param_type = param_type.__supertype__

                    if param.default is Parameter.empty:
                        message_fields[name] = create_field_from_type(param_type, converters=converters)
                    else:
                        message_fields[name] = create_field_from_type(param_type,
                                                                      converters=converters,
                                                                      default=param.default)

                request = message_factory(f'{upper_camelcase(func_name)}Request', message_fields)
    else:  # func(self)
        if request is None:
            request = Empty

        # either request is Empty, or otherwise all request fields are discarded -- strange, but valid
        unpack_request = ()

    return_type = func_type_hints.get('return', Any)
    response_converter = None

    if response is None:
        if hasattr(return_type, '__supertype__'):  # handles NewType
            return_type = return_type.__supertype__

        if return_type in (Any, None, type(None)):  # None for Python 3.5 compatibility
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
                raise RuntimeError(f"Unable to coerce return value to wire format: "
                                   f"'{return_type}' in {func}")
    elif return_type == Any:
        # NOTE missing return type annotation (assuming 'response' here)
        pass
    elif return_type in (None, type(None)):  # None for Python 3.5 compatibility
        response = Empty
    elif response != return_type:
        for converter in converters:
            if converter.wire == response and converter.python == return_type:
                response_converter = converter
                break

        if not response_converter:
            raise RuntimeError(f"Unable to coerce return value to wire format: "
                               f"'{return_type}' in {func}")

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
        async def invokable(inst, req: Message, loop: 'asyncio.AbstractEventLoop' = None) -> Message:
            return wrap_response(await func(inst,
                                            *(await asyncio.gather(*[arg.resolve(inst, req)
                                                                     for arg in additional_args], loop=loop)),
                                            *wrap_args(req),
                                            **wrap_kwargs(req)))
    else:
        async def invokable(inst, req: Message, loop: 'asyncio.AbstractEventLoop' = None) -> Message:
            return wrap_response(await func(inst, *wrap_args(req), **wrap_kwargs(req)))

    return MessageFunction(request, response, wraps(func)(invokable))
