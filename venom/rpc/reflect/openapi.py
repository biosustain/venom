from collections import defaultdict
from itertools import groupby, chain

from typing import Iterable, Type

from venom import Message
from venom.fields import FieldDescriptor
from venom.message import fields, is_empty
from venom.protocol import JSONProtocol, Protocol
from venom.protocol.transcode import JSONTimestampTranscoder, DictMessageTranscoder, \
    JSONValueTranscoder, JSONFieldMaskTranscoder, JSONTranscoder
from venom.rpc.method import Method, HTTPFieldLocation
from venom.rpc.reflect.reflect import Reflect
from venom.rpc.reflect.stubs import OperationMessage, \
    ParameterMessage, ResponsesMessage, ResponseMessage, \
    SchemaMessage, InfoMessage, OpenAPISchema, TagMessage

DESCRIPTION = 'description'


# TODO: other types
TYPE_TO_JSON = {
    str: 'string',
    int: 'integer',
    float: 'double',
    bool: 'boolean',
}

PATH_PARAMETER = {
    'in_': 'path',
    'required': True
}

BODY_PARAMETER = {
    'in_': 'body',
}

QUERY_PARAMETER = {
    'in_': 'query',
}


def message_reference_schema(message: Type[Message], protocol: Type[Protocol] = None) -> SchemaMessage:
    if protocol:
        transcoder = DictMessageTranscoder.get(protocol, message)

        if transcoder == JSONTimestampTranscoder:
            return SchemaMessage(type='string', format='date-time')
        elif transcoder == JSONFieldMaskTranscoder:
            return SchemaMessage(type='string')
        elif transcoder == JSONValueTranscoder:
            return field_schema(message.value)
        elif transcoder == JSONTranscoder:
            return SchemaMessage(type='object', description='JSON object')
        elif not issubclass(transcoder, DictMessageTranscoder):
            raise NotImplementedError(f'Unsupported transcoder for reflection {transcoder} on {message}')

    return SchemaMessage(ref=f'#/definitions/{message.__meta__.name}')


def field_schema(field: FieldDescriptor, protocol: Type[Protocol] = None) -> SchemaMessage:
    if issubclass(field.type, Message):
        schema = message_reference_schema(field.type, protocol)
    elif field.type not in TYPE_TO_JSON:
        raise NotImplementedError(f'Unrecognized field type: {field.type}')
    else:
        schema = SchemaMessage(type=TYPE_TO_JSON[field.type])

    if field.repeated:
        if field.key_type:
            return SchemaMessage(type='object',
                                 additional_properties=schema,
                                 description=field.options.get('description'))
        return SchemaMessage(type='array',
                             items=schema,
                             description=field.options.get('description'))

    if not schema.ref:  # {$ref} objects should not have additional properties
        schema.description = field.options.get(DESCRIPTION)

    return schema


def fields_schema(fields: Iterable[FieldDescriptor],
                  protocol: Type[Protocol] = None,
                  description: str = None) -> SchemaMessage:
    return SchemaMessage(type='object',
                         properties={field.json_name: field_schema(field, protocol) for field in fields},
                         description=description)


def parameters_at_location(request: Message, names: Iterable, default: dict):
    encoder = DictMessageTranscoder(JSONProtocol, SchemaMessage)

    for field_name in names:
        field = getattr(request, field_name)
        schema = field_schema(field)

        yield ParameterMessage(
            name=field.json_name,
            **default,
            **encoder.encode(schema))


def parameters_path(method: Method) -> Iterable:
    return parameters_at_location(
        method.request,
        method.http_path_parameters(),
        PATH_PARAMETER)


def parameters_query(method: Method) -> Iterable:
    return parameters_at_location(
        method.request,
        method.http_field_locations()[HTTPFieldLocation.QUERY],
        QUERY_PARAMETER)


def parameters_body(method: Method) -> list:
    body_fields = method.http_field_locations()[HTTPFieldLocation.BODY]

    if not body_fields:
        return []

    fields = {f: getattr(method.request, f) for f in body_fields}
    if fields == method.request.__fields__:
        param = dict(
            name=method.request.__meta__.name,
            schema=message_reference_schema(method.request, JSONProtocol))
    else:
        param = dict(
            name=method.name + '_body',
            schema=fields_schema(fields.values(), JSONProtocol))
    return [ParameterMessage(**BODY_PARAMETER, **param)]


def response_message(method: Method) -> ResponseMessage:
    return ResponseMessage(
        description=method.options.get(DESCRIPTION, ''),
        schema=message_reference_schema(method.response, JSONProtocol))


def operation_message(method: Method) -> OperationMessage:
    return OperationMessage(
        summary=method.options.get(DESCRIPTION, ''),
        tags=method.options.get('tags', []),
        responses=ResponsesMessage(default=response_message(method)),
        parameters=list(chain(
            parameters_body(method),
            parameters_path(method),
            parameters_query(method))))


def schema_for_message(message: Message, protocol: Protocol = None) -> SchemaMessage:
    return fields_schema(fields(message),
                         JSONProtocol,  # XXX
                         description=message.__meta__.get('description'))


def make_openapi_schema(reflect: Reflect) -> OpenAPISchema:
    tags = []
    paths = defaultdict(dict)
    for path, group in groupby(reflect.methods, key=lambda method: method.format_http_path(json_names=True)):
        for method in group:
            if method.options.get('tags'):
                tags.extend([TagMessage(name=n) for n in method.options['tags']])
            paths[path][method.http_method.value.lower()] = operation_message(method)

    return OpenAPISchema(
        swagger='2.0',
        consumes=['application/json'],
        produces=['application/json'],
        tags=tags,
        info=InfoMessage(version=reflect.version, title=reflect.title),
        paths=dict(paths),
        definitions={
            message.__meta__.name: schema_for_message(message)
            for message in reflect.messages
            if not is_empty(message) and
               issubclass(DictMessageTranscoder.get(JSONProtocol, message), DictMessageTranscoder)
        }
    )
