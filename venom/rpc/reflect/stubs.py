from venom import Message
from venom.fields import Field, Repeat, String, Map, Bool
from venom.rpc import Stub
from venom.rpc import http


class SchemaMessage(Message):
    type = String()  # TODO: enum
    description = String()
    properties = Map(Field('venom.rpc.reflect.openapi.SchemaMessage'))
    ref = String(json_name='$ref')
    additional_properties = Field('venom.rpc.reflect.openapi.SchemaMessage')
    items = Field('venom.rpc.reflect.openapi.SchemaMessage')


class ParameterMessage(Message):
    is_in = String(json_name='in')  # TODO: enum
    description = String()
    required = Bool()
    name = String()
    type = String()
    items = Field(SchemaMessage)
    schema = Field(SchemaMessage)


class ResponseMessage(Message):
    description = String()
    schema = Field(SchemaMessage)


class ResponsesMessage(Message):
    default = Field(ResponseMessage)  # TODO: error codes


class OperationMessage(Message):
    produces = Repeat(String())
    responses = Field(ResponsesMessage)
    parameters = Repeat(ParameterMessage)


class InfoMessage(Message):
    version = String()
    title = String()
    description = String()
    terms_of_service = String()
    contact = String()
    license = String()


class OpenAPISchema(Message):
    swagger = String()
    schemes = Repeat(String())
    consumes = Repeat(String())
    produces = Repeat(String())
    info = Field(InfoMessage)
    host = String()
    base_path = String()
    paths = Map(Map(Field(OperationMessage)))
    definitions = Map(Field(SchemaMessage))


class ReflectStub(Stub):
    @http.GET('/openapi.json')
    def get_openapi_schema(self) -> OpenAPISchema:
        raise NotImplementedError()
