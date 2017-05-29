from venom import Message
from venom.fields import Field, String, Map, MapField, Repeat
from venom.rpc import Stub
from venom.rpc import http
from venom.validation import Schema


class SchemaMessage(Schema):
    ref = String(json_name='$ref')

    type: str  # TODO: enum
    description: str

    items = Field('venom.rpc.reflect.openapi.SchemaMessage')

    properties = MapField('venom.rpc.reflect.openapi.SchemaMessage')
    additional_properties = Field('venom.rpc.reflect.openapi.SchemaMessage')


class ParameterMessage(Message):
    in_ = String(json_name='in')  # TODO: enum
    description: str
    required: bool
    name: str
    type: str
    items: SchemaMessage
    schema: SchemaMessage


class ResponseMessage(Message):
    description: str
    schema: SchemaMessage


class ResponsesMessage(Message):
    default: ResponseMessage  # TODO: error codes


class ExternalDocsMessage(Message):
    description: str
    url: str


class OperationMessage(Message):
    summary: str
    description: str
    tags: Repeat[str]
    produces: Repeat[str]
    responses: ResponsesMessage
    parameters: Repeat[ParameterMessage]
    deprecated: bool
    external_docs: ExternalDocsMessage


class InfoMessage(Message):
    version: str
    title: str
    description: str
    terms_of_service: str
    contact: str
    license: str


class PathsMessage(Message):
    get: OperationMessage
    put: OperationMessage
    post: OperationMessage
    delete: OperationMessage
    options: OperationMessage
    head: OperationMessage
    patch: OperationMessage


class TagMessage(Message):
    name: str
    description: str
    external_docs: ExternalDocsMessage


class OpenAPISchema(Message):
    swagger: str
    schemes: Repeat[str]
    consumes: Repeat[str]
    produces: Repeat[str]
    tags: Repeat[TagMessage]
    info: InfoMessage
    host: str
    base_path: str
    paths: Map[str, PathsMessage]
    definitions: Map[str, SchemaMessage]


class ReflectStub(Stub):
    @http.GET('/openapi.json')
    def get_openapi_schema(self) -> OpenAPISchema:
        raise NotImplementedError()
