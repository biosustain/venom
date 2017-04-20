from abc import ABC, abstractmethod
from functools import partial
from weakref import WeakKeyDictionary

from typing import Type, TypeVar, Callable, Any, Tuple, Union, Mapping

from venom import Message
from venom.exceptions import ValidationError
from venom.fields import FieldDescriptor, Repeat
from venom.message import fields, merge_into
from venom.validation._validators import min_length, max_length, pattern, min_items, max_items, minimum, maximum
from .schema import Schema

M = TypeVar('M', bound=Message)


def _get_field_schema(field: FieldDescriptor, extension: Schema = None) -> Schema:
    return merge_into(Schema(), Schema.lookup(field.type), field.schema or Schema(), extension or Schema())


class _MessageValidator(ABC):
    __msg_validators = WeakKeyDictionary()

    def __new__(cls, msg: Type[Message], **kwargs):
        try:
            return cls.__msg_validators[msg]
        except KeyError:
            pass

        instance = super(_MessageValidator, cls).__new__(cls)
        instance.__init__(msg, **kwargs)
        return instance

    def __init__(self, msg: Type[M], *, register: bool = True):
        if register:
            self.__msg_validators[msg] = self
        self._message_cls = msg

    @abstractmethod
    def validate(self, instance: M) -> None:
        raise NotImplementedError


class MessageValidator(_MessageValidator):

    def __init__(self, msg: Type[M], *, field_schema_extensions: Mapping[str, Schema] = None):
        super().__init__(msg, register=field_schema_extensions is None)

        if field_schema_extensions is None:
            field_schema_extensions = {}

        self._field_validators = tuple((field.name,
                                        _FieldValidator(field,
                                                        _get_field_schema(field,
                                                                          field_schema_extensions.get(field.name))))
                                       for field in fields(msg))

    def validate(self, message: M) -> None:
        for name, validator in self._field_validators:
            try:
                validator.validate(message[name])
            except ValidationError as v:
                v.path.insert(0, name)
                raise v


_ValidationFunction = Callable[[Any], None]


def _repeat(validations: Tuple[_ValidationFunction], instance: Union[list, dict]):
    for index, value in enumerate(instance):
        try:
            for validate in validations:
                validate(value)
        except ValidationError as v:
            v.path.insert(0, index)
            raise v


class _FieldValidator(object):
    __slots__ = ('_validations',)

    def __init__(self, field: FieldDescriptor, schema: Schema):
        self._validations = self._get_validations(field, schema)

    @classmethod
    def _get_validations(cls, field: FieldDescriptor, schema: Schema) -> Tuple[_ValidationFunction, ...]:
        validations = ()

        if issubclass(field.type, Message):
            validator = MessageValidator(field.type)
            return validator.validate,
        elif field.type in (str, bytes):
            if schema.min_length > 0:
                validations += partial(min_length, schema),
            if schema.max_length > 0:
                validations += partial(max_length, schema),
            if schema.pattern:
                validations += partial(pattern, schema),
        elif field.type in (int, float):
            if schema.minimum > 0:
                validations += partial(minimum, schema),
            if schema.maximum > 0:
                validations += partial(maximum, schema),
        else:
            raise NotImplementedError

        if field.repeated:
            value_validations = validations
            validations = ()

            if field.key_type:
                raise NotImplementedError
            else:
                if schema.min_items and schema.max_items.value > 0:
                    validations += partial(min_items, schema),
                if schema.max_items and schema.max_items.value > 0:
                    validations += partial(max_items, schema),

            if value_validations:
                validations += partial(_repeat, value_validations),
        return validations

    def validate(self, instance: Any):
        for validate in self._validations:
            validate(instance)
