from collections import namedtuple
from inspect import signature, Parameter
from typing import Callable, Any, Sequence, get_type_hints, Type, NamedTuple
from typing import Tuple
from typing import Union

from six import wraps
from venom.fields import RepeatField, MapField

from venom.converter import Converter

from venom.message import Empty, Message, get_or_default

MagicFunction = NamedTuple('MagicFunction', [
    ('request', Type[Message]),
    ('response', Type[Message]),
    ('func', Callable[..., Any]),
    ('invokable', Callable[[Any, Message], Message])
])


# TODO name arg for use with auto-generation
def magic(func: Callable[..., Any],
          request: Type[Message] = None,
          response: Type[Message] = None,
          converters: Sequence[Converter] = ()) -> MagicFunction:
    # TODO parameters supplied by the service implementation through a context; session etc.

    func_signature = signature(func)
    func_type_hints = get_type_hints(func)

    if len(func_signature.parameters) == 0:
        # no "self" parameter: func()
        raise RuntimeError("At least one argument expected in {}".format(func))

    request_converter = None
    func_parameters = tuple(func_signature.parameters.items())[1:]

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

    if unpack_request is True:
        wrap_request = lambda inst, req: func(inst, **req)
    elif unpack_request is False:
        if request_converter:
            wrap_request = lambda inst, req: func(inst, request_converter.convert(req))
        else:
            wrap_request = func
    elif unpack_request == ():
        wrap_request = lambda inst, req: func(inst)
    else:
        wrap_request = lambda inst, req: func(inst, **{f: get_or_default(req, f, d) for f, d in unpack_request})

    # TODO (optimization) combine into just one level of wrapping
    if response == Empty and return_type != Empty:
        def invokable(inst, req: Message) -> Empty:
            wrap_request(inst, req)
            return Empty()
    elif response_converter:
        def invokable(inst, req: Message) -> Message:
            return response_converter.format(wrap_request(inst, req))
    else:
        invokable = wrap_request

    return MagicFunction(request, response, func, wraps(func)(invokable))
