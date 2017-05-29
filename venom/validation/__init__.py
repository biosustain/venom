from abc import ABC, abstractmethod
from functools import partial
from weakref import WeakKeyDictionary

from typing import Type, TypeVar, Callable, Any, Tuple, Union

from venom import Message
from venom.exceptions import ValidationError
from venom.fields import FieldDescriptor
from venom.message import fields, merge_into
from venom.validation._validators import min_length, max_length, pattern, min_items, max_items, minimum, maximum
from .schema import Schema

M = TypeVar('M', bound=Message)


def _get_field_schema(field: FieldDescriptor) -> Schema:
    return merge_into(Schema(), field.schema or Schema())


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
    def __init__(self, msg: Type[M]):
        super().__init__(msg)

        # TODO only create validators where the schema is not empty

        field_schemas = ((field, _get_field_schema(field)) for field in fields(msg))
        self._field_validators = tuple((field.name, _FieldValidator(field, schema))
                                       for field, schema in field_schemas
                                       if schema != Schema())

    def validate(self, message: M) -> None:
        for name, validator in self._field_validators:
            try:
                validator.validate(message.get(name))
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

        if schema == Schema():
            return ()

        if issubclass(field.type, Message):
            validator = MessageValidator(field.type)
            return validator.validate,
        elif field.type in (str, bytes):
            if schema.min_length > 0:
                validations += partial(min_length, schema),
            if schema.max_length is not None:
                validations += partial(max_length, schema),
            if schema.pattern:
                validations += partial(pattern, schema),
        elif field.type in (int, float):
            if schema.minimum is not None:
                validations += partial(minimum, schema),
            if schema.maximum is not None:
                validations += partial(maximum, schema),
        else:
            raise NotImplementedError

        if field.repeated:
            value_validations = validations
            validations = ()

            if field.key_type:
                raise NotImplementedError
            else:
                if schema.min_items > 0:
                    validations += partial(min_items, schema),
                if schema.max_items is not None:
                    validations += partial(max_items, schema),

            if value_validations:
                validations += partial(_repeat, value_validations),
        return validations

    def validate(self, instance: Any):
        for validate in self._validations:
            validate(instance)
