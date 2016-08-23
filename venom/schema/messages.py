from venom.fields import String, Map, Repeat, Number, Field, Integer, Boolean
from venom.message import Message, one_of

JSON_SCHEMA_TYPES = ('integer', 'number', 'string', 'boolean', 'object', 'array')

class FieldSchema(Message):

    # one_of(
    #     type=String(choices=JSON_SCHEMA_TYPES),
    #     reference=String(attribute='$ref'))

    type = String(choices=JSON_SCHEMA_TYPES)
    minimum = Number(optional=True)
    maximum = Number(optional=True)
    exclusive_minimum = Number(optional=True)
    exclusive_maximum = Number(optional=True)
    min_length = Number(optional=True)
    max_length = Number(optional=True)
    pattern = String(optional=True)
    format = String(optional=True)
    # TODO
    # enum = Repeat(Value, optional=True)
    # default = Property(Value)


class RepeatFieldSchema(FieldSchema):
    items = Field('venom.schema.messages.PropertySchema', optional=True)
    unique_items = Boolean(optional=True)
    min_items = Integer(optional=True)
    max_items = Integer(optional=True)


class MapFieldSchema(FieldSchema):
    properties = Field('venom.schema.messages.PropertySchema', optional=True)
    min_properties = Integer(optional=True)
    max_properties = Integer(optional=True)


class MessageReference(Message):
    uri = String(attribute='$ref')


class PropertySchema(Message):
    schema = one_of('reference',
                    'field_schema',
                    'repeat_property_schema',
                    'map_property_schema')

    reference = Field(MessageReference)
    field_schema = Field(FieldSchema)
    map_field_schema = Field(MapFieldSchema)
    repeat_field_schema = Field(RepeatFieldSchema)


class MessageSchema(Message):
    type = String(choices=('object'))
    properties = Map(PropertySchema)
    required = Repeat(String(), optional=True)