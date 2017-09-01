import os
from unittest import TestCase

from venom.common import Timestamp, StringValue, JSONValue
from venom.fields import Int, String, repeated, Field
from venom.message import Message, Empty
from venom.protocol import JSONProtocol
from venom.rpc import Service, http, Venom
from venom.rpc.reflect.openapi import make_openapi_schema, OpenAPISchema, \
    SchemaMessage
from venom.rpc.reflect.stubs import TagMessage
from venom.validation import MessageValidator
from venom.exceptions import ValidationError

import json
from venom.rpc.reflect.reflect import Reflect
from venom.rpc.reflect.service import ReflectService
from venom.rpc.reflect.stubs import ParameterMessage, ResponseMessage

TEST_DIR = os.path.dirname(__file__)


class OpenAPITestCase(TestCase):
    def test_openapi_simple(self):
        class PetSimple(Message):
            id: int

        class PetServiceSimple(Service):
            class Meta:
                name = 'PetService'

            @http.GET('./pet/{id}')
            def get_pet(self, request: PetSimple) -> PetSimple:
                return request

            @http.POST('./pet')
            def create_pet_body(self, request: PetSimple) -> PetSimple:
                return request

        reflect = Reflect()
        reflect.add(PetServiceSimple)
        schema = make_openapi_schema(reflect)
        protocol = JSONProtocol(OpenAPISchema)
        with open(TEST_DIR + '/data/openapi_simple.json', 'rb') as f:
            schema_correct = protocol.unpack(f.read())
            self.assertEqual(schema.paths, schema_correct.paths)
            self.assertEqual(schema.definitions, schema_correct.definitions)

    def test_openapi_paths(self):
        class Pet(Message):
            id = Int()
            name = String()
            tag = String()

        class PetServicePaths(Service):
            class Meta:
                name = 'pets'

            @http.GET('./pet/{id}', description='Get the pet')
            def get_pet(self, request: Pet) -> Pet:
                return Pet(request.id, 'Berry', 'cat')

            @http.POST('./pet/{id}', description='Post the pet with path id')
            def create_pet(self, request: Pet) -> Pet:
                return request

            @http.POST('./pet', description='Post the pet with body params')
            def create_pet_body(self, request: Pet) -> Pet:
                return request

            @http.GET('./pet', description='Get the pet with query arguments')
            def query_pet(self, request: Pet) -> Pet:
                return request

        reflect = Reflect()
        reflect.add(PetServicePaths)
        schema = make_openapi_schema(reflect)
        self.assertEqual(set(schema.paths.keys()), {'/pets/pet', '/pets/pet/{id}'})
        self.assertEqual(set(schema.paths['/pets/pet'].keys()), {'post', 'get'})
        self.assertEqual(set(schema.paths['/pets/pet/{id}'].keys()), {'post', 'get'})

    def test_openapi_path_params_camelcase(self):
        class GetPetRequest(Message):
            pet_id = Int()

        class PetServicePaths(Service):
            class Meta:
                name = 'pets'

            @http.GET('/pet')
            def get_pet(self, request: GetPetRequest) -> Empty:
                pass

            @http.GET('/pet/{pet_id}')
            def get_pet_path(self, request: GetPetRequest) -> Empty:
                pass

        reflect = Reflect()
        reflect.add(PetServicePaths)
        schema = make_openapi_schema(reflect)

        self.assertEqual(set(schema.paths.keys()), {'/pet', '/pet/{petId}'})
        self.assertEqual(list(schema.paths['/pet']['get'].parameters), [
            ParameterMessage(in_='query', name='petId', type='integer')
        ])

        self.assertEqual(list(schema.paths['/pet/{petId}']['get'].parameters), [
            ParameterMessage(in_='path', required=True, name='petId', type='integer')
        ])

    def test_openapi_custom_transcoder(self):
        class UpdateDateRequest(Message):
            new_date: Timestamp
            reason: StringValue

        class DateService(Service):

            @http.GET
            def get_current_time(self) -> Timestamp:
                pass

            @http.POST('.')
            def update_date(self, request: UpdateDateRequest):
                pass

        reflect = Reflect()
        reflect.add(DateService)
        schema = make_openapi_schema(reflect)

        self.assertEqual(set(schema.paths.keys()), {'/date/get-current-time', '/date'})

        self.assertEqual(schema.paths['/date/get-current-time']['get'].responses.default,
                         ResponseMessage(description='',
                                         schema=SchemaMessage(type='string', format='date-time')))

        self.assertEqual(set(schema.definitions.keys()), {'UpdateDateRequest'})
        self.assertEqual(schema.definitions['UpdateDateRequest'], SchemaMessage(
            properties={
                'newDate': SchemaMessage(type='string', format='date-time'),
                'reason': SchemaMessage(type='string')},
            type='object'))

    def test_nested_messages(self):
        class Pet(Message):
            class Meta:
                description = 'Very important object'

            pet_id = String(description='Pet ID to query')

        class QueryResponse(Message):
            class Meta:
                description = 'Information about pets'

            ids = repeated(Field(Pet, description='Bunch of pets'))
            pet = Field(Pet, description='The other pet')
            repeat = repeated(String(description='Bunch of strings'))

        class PetMapping(Service):
            class Meta:
                version = '0.0.1b'
                name = 'Pet Mapper'

            @http.GET('./query', description='Get the pet')
            def query(self) -> QueryResponse:
                return QueryResponse(ids=['1', '2', '3'])

        reflect = Reflect()
        reflect.add(PetMapping)
        reflect.add(ReflectService)
        schema = make_openapi_schema(reflect)
        response = SchemaMessage(
            description='Information about pets',
            type='object',
            properties=dict(
                ids=SchemaMessage(
                    type='array',
                    description='Bunch of pets',
                    items=SchemaMessage(ref='#/definitions/Pet')
                ),
                pet=SchemaMessage(ref='#/definitions/Pet'),
                repeat=SchemaMessage(
                    type='array',
                    description='Bunch of strings',
                    items=SchemaMessage(type='string')
                ),
            ),
        )
        self.assertEqual(schema.definitions['QueryResponse'], response)

    def test_venom_info(self):
        venom = Venom(version='3.1.4', title='Pet Aggregator')
        venom.add(ReflectService)
        schema = make_openapi_schema(
            venom.get_instance(ReflectService).reflect
        )
        self.assertEqual(schema.info.version, '3.1.4')
        self.assertEqual(schema.info.title, 'Pet Aggregator')

    def test_tags(self):
        class QueryResponse(Message):
            name: str

        class PetMapping(Service):
            @http.GET('./query', tags=['pets'])
            def query(self) -> QueryResponse:
                return QueryResponse(name='pet')

        reflect = Reflect()
        reflect.add(PetMapping)
        reflect.add(ReflectService)
        schema = make_openapi_schema(reflect)
        self.assertEqual(
            list(schema.tags),
            [TagMessage(name='pets')]
        )
        self.assertEqual(
            list(schema.paths['/petmapping/query']['get'].tags),
            ['pets']
        )

    def test_json_value(self):
        class JsonResponse(Message):
            value: JSONValue

        class Run(Service):
            @http.GET('.', description='Response')
            def query(self) -> JsonResponse:
                return JsonResponse(value={'a': [1, 2]})

        reflect = Reflect()
        reflect.add(Run)
        schema = make_openapi_schema(reflect)
        self.assertEqual(
            schema.definitions['JsonResponse'],
            SchemaMessage(properties={'value': SchemaMessage(type='object')}, type='object')
        )
