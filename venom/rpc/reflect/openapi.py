from collections import defaultdict
from functools import singledispatch
from itertools import groupby, chain
from operator import attrgetter

from typing import Iterable

from venom import Message
from venom.fields import Field, RepeatField, MapField
from venom.message import fields, is_empty
from venom.protocol import JSON
from venom.rpc.method import Method, HTTPFieldLocation
from venom.rpc.reflect.reflect import Reflect
from venom.rpc.reflect.stubs import OperationMessage, \
    ParameterMessage, ResponsesMessage, ResponseMessage, \
    SchemaMessage, InfoMessage, OpenAPISchema

DESCRIPTION = 'description'

# TODO: other types
TYPE_TO_JSON = {
    str: 'string',
    int: 'integer',
    float: 'double',
    bool: 'boolean',
}

PATH_PARAMETER = {
    'is_in': 'path',
    'required': True
}

BODY_PARAMETER = {
    'is_in': 'body',
}

QUERY_PARAMETER = {
    'is_in': 'query',
}


def ref_schema_message(message: Message) -> SchemaMessage:
    return SchemaMessage(ref=f'#/definitions/{message.__meta__.name}')


@singledispatch
def schema_message(field: Field) -> SchemaMessage:
    if field.type not in TYPE_TO_JSON:
        if issubclass(field.type, Message):
            return ref_schema_message(field.type)
        return schema_message(field.type)
    return SchemaMessage(
        type=TYPE_TO_JSON[field.type],
        description=field.options.get(DESCRIPTION),
    )


@schema_message.register(RepeatField)
def schema_message_repeat(field: RepeatField) -> SchemaMessage:
    return SchemaMessage(
        type='array',
        items_=schema_message(field.items),
        description=field.options.get(DESCRIPTION),
    )


@schema_message.register(MapField)
def schema_message_map(field: MapField) -> SchemaMessage:
    return SchemaMessage(
        type='object',
        additionalProperties=schema_message(field.values),
        description=field.options.get(DESCRIPTION),
    )


def parameters_at_location(request: Message, names: Iterable, default: dict):
    for field_name in names:
        field = getattr(request, field_name)
        field_schema = schema_message(field)
        protocol = JSON(type(field_schema))
        yield ParameterMessage(
            name=field.json_name,
            **default,
            **protocol.encode(field_schema),
        )


def parameters_path(method: Method) -> Iterable:
    return parameters_at_location(
        method.request,
        method.http_path_parameters(),
        PATH_PARAMETER
    )


def parameters_query(method: Method) -> Iterable:
    return parameters_at_location(
        method.request,
        method.http_field_locations()[HTTPFieldLocation.QUERY],
        QUERY_PARAMETER
    )


def parameters_body(method: Method) -> list:
    body_fields = method.http_field_locations()[HTTPFieldLocation.BODY]
    if not body_fields:
        return []
    fields = {f: getattr(method.request, f) for f in body_fields}
    if fields == method.request.__fields__:
        param = dict(
            name=method.request.__meta__.name,
            schema=ref_schema_message(method.response)
        )
    else:
        param = dict(
            name=method.name + '_body',
            schema=schema_for_fields(fields.values())
        )
    return [ParameterMessage(**BODY_PARAMETER, **param)]


def response_message(method: Method) -> ResponseMessage:
    return ResponseMessage(
        description=method.options.get(DESCRIPTION, ''),
        schema=ref_schema_message(method.response)
    )


def operation_message(method: Method) -> OperationMessage:
    return OperationMessage(
        responses=ResponsesMessage(default=response_message(method)),
        parameters=list(chain(
            parameters_body(method),
            parameters_path(method),
            parameters_query(method)
        ))
    )


def schema_for_fields(fields, description=None) -> SchemaMessage:
    return SchemaMessage(
        type='object',
        properties={
            v.json_name: schema_message(v) for v in fields
        },
        description=description,
    )


def schema_for_message(message: Message) -> SchemaMessage:
    return schema_for_fields(
        fields(message),
        description=message.__meta__.get(DESCRIPTION)
    )


def make_openapi_schema(reflect: Reflect) -> OpenAPISchema:
    paths = defaultdict(dict)
    for path, group in groupby(reflect.methods, key=attrgetter('http_path')):
        for method in group:
            paths[path.strip('.')][method.http_method.value.lower()] = operation_message(method)
    definitions = {
        m.__meta__.name: schema_for_message(m) for m in reflect.messages
        if not is_empty(m)
    }
    return OpenAPISchema(
        swagger='2.0',
        consumes=['application/json'],
        produces=['application/json'],
        info=InfoMessage(version=reflect.version, title=reflect.title),
        paths=dict(paths),
        definitions=definitions,
    )
