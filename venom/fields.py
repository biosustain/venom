from importlib import import_module

from typing import TypeVar, Generic, Any, Union, Type, Sequence, List, Mapping, Iterable, Tuple, MutableMapping, \
    Iterator, Dict, MutableSequence, overload

from venom.util import cached_property, AttributeDict, camelcase


_KT = TypeVar('_KT', str, int)

_VT = TypeVar('_VT', bool, int, float, str, bytes, 'venom.message.Message')


class FieldDescriptor(Generic[_VT]):
    _type: Union[Type[_VT], str]
    _name: str = None
    _json_name: str = None

    schema: 'venom.validation.Schema' = None
    options: Mapping[str, Any]
    
    repeated: bool = False
    key_type: type = None

    def __init__(self,
                 type_: Union[Type[_VT], str],
                 name: str = None,
                 *,
                 json_name: str = None,
                 schema: 'venom.validation.schema' = None,
                 options: Mapping[str, Any] = None):
        self._type = type_
        self._name = name
        self._json_name = json_name
        self.schema = schema
        self.key_type = None
        self.options = AttributeDict(options or {})

    def __set_name__(self, owner, name):
        if self._name is None:
            self._name = name

    # TODO wait on https://github.com/python/mypy/issues/244
    def __set__(self, instance: 'venom.message.Message', value: _VT):
        instance[self.name] = value

    def __get__(self, instance: 'venom.message.Message', owner):
        if instance is None:
            return self
        try:
            return instance[self.name]
        except KeyError:
            return self.default()

    @cached_property
    def type(self) -> Type[_VT]:
        if isinstance(self._type, str):
            if '.' in self._type:
                module_name, class_name = self._type.rsplit('.', 1)
                module = import_module(module_name)
                return getattr(module, class_name)

            raise RuntimeError('Unable to resolve: {} in {}'.format(self._type, repr(self)))
        return self._type

    @property
    def descriptor_type_hint(self) -> type:
        if self.repeated:
            if self.key_type:
                return Dict[self.key_type, self.type]
            return List[self.type]
        else:
            return self.type

    @property
    def json_name(self):
        if self._json_name is None:
            return camelcase(self.name)
        return self._json_name

    @property
    def name(self):
        return self._name

    def default(self):
        return None

    def __eq__(self, other):
        if not isinstance(other, FieldDescriptor):
            return False
        return self._name == other._name and \
               self._json_name == other._json_name and \
               self.type == other.type and \
               self.repeated == other.repeated and \
               self.key_type == other.key_type and \
               self.schema == other.schema and \
               self.options == other.options

    def __repr__(self):
        type_ = self._type.__qualname__ if not isinstance(self._type, str) else repr(self._type)

        if self.repeated:
            if self.key_type:
                type_ = f'Map[{self.key_type.__qualname__}, {type_}]'
            else:
                type_ = f'Repeat[{type_}]'

        if self.name:
            return f'<{self.__class__.__qualname__} {self.name}: {type_}>'
        return f'<{self.__class__.__qualname__} {type_}>'

    def __hash__(self):
        return hash(repr(self))


class Field(Generic[_VT], FieldDescriptor):
    def __init__(self,
                 type_: Union[Type[_VT], str],
                 name: str = None,
                 *,
                 default: Any = None,
                 json_name: str = None,
                 schema: 'venom.validation.Schema' = None,
                 **options) -> None:
        super(Field, self).__init__(type_, name, json_name=json_name, schema=schema, options=options)
        self._default = default

    def default(self):
        if self._default is None:
            return self.type()
        return self._default

    @cached_property
    def type(self) -> Type[_VT]:
        if isinstance(self._type, str):
            if '.' in self._type:
                module_name, class_name = self._type.rsplit('.', 1)
                module = import_module(module_name)
                return getattr(module, class_name)

            raise RuntimeError('Unable to resolve: {} in {}'.format(self._type, repr(self)))
        return self._type

    def __eq__(self, other):
        if not isinstance(other, Field):
            return False
        return self.type == other.type and self.options == other.options

    def __hash__(self):
        return hash(repr(self))

_PT = TypeVar('PT')


class ConverterField(Field[_VT], Generic[_VT, _PT]):
    def __init__(self,
                 converter: 'venom.converter.Converter[_VT, _PT]',
                 **kwargs) -> None:
        super().__init__(converter.wire, **kwargs)
        self.converter = converter

    def __set__(self, instance: 'venom.Message', value: _PT) -> None:
        instance[self.name] = self.converter.format(value)

    @overload
    def __get__(self, instance: None, owner) -> 'ConverterField[_VT, _PT]':
        pass

    @overload
    def __get__(self, instance: 'venom.Message', owner) -> _PT:
        pass

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return self.converter.resolve(instance.get(self.name))


class String(Field[str]):
    def __init__(self, **kwargs) -> None:
        super().__init__(str, **kwargs)


class Bytes(Field[bytes]):
    def __init__(self, **kwargs) -> None:
        super().__init__(bytes, **kwargs)


class Bool(Field[bool]):
    def __init__(self, **kwargs) -> None:
        super().__init__(bool, **kwargs)


class Int32(Field[int]):
    def __init__(self, **kwargs) -> None:
        super().__init__(int, **kwargs)


class Int64(Field[int]):
    def __init__(self, **kwargs) -> None:
        super().__init__(int, **kwargs)


Integer = Int = Int64


class Float32(Field[float]):
    def __init__(self, **kwargs) -> None:
        super().__init__(float, **kwargs)


class Float64(Field[float]):
    def __init__(self, **kwargs) -> None:
        super().__init__(float, **kwargs)


Number = Float64


class Repeat(Generic[_VT], MutableSequence[_VT]):
    def __init__(self, message: 'venom.message.Message', name: str):
        self.message = message
        self.name = name

    @property
    def _sequence(self) -> list:
        try:
            return self.message[self.name]
        except KeyError:
            return []

    def __len__(self):
        return len(self._sequence)

    def __getitem__(self, index):
        return self._sequence[index]

    def insert(self, index, value):
        self.message[self.name] = sequence = self._sequence
        sequence.insert(index, value)

    def __delitem__(self, index):
        self.message[self.name] = sequence = self._sequence
        del sequence[index]

    def __setitem__(self, index, value):
        self.message[self.name] = sequence = self._sequence
        sequence[index] = value

    def __iter__(self):
        return iter(self._sequence)

    def items(self) -> Iterable[Tuple[int, Any]]:
        return enumerate(self._sequence)

    def __repr__(self):
        return f'Repeat({repr(self._sequence)})'


class RepeatField(FieldDescriptor[_VT]):
    repeated: bool = True

    @overload
    def __get__(self, instance: None, owner) -> 'RepeatField[_VT]':
        pass

    @overload
    def __get__(self, instance: 'venom.message.Message', owner) -> Repeat[_VT]:
        pass

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return Repeat(instance, self.name)


class Map(Generic[_KT, _VT], MutableMapping[_KT, _VT]):
    def __init__(self, message: 'venom.message.Message', name: str):
        self.message = message
        self.name = name

    @property
    def _mapping(self) -> Dict[_KT, _VT]:
        try:
            return self.message[self.name]
        except KeyError:
            return {}

    def __getitem__(self, k: _KT) -> _VT:
        return self._mapping[k]

    def __setitem__(self, k: _KT, v: _VT) -> None:
        self._mapping[k] = v

    def __delitem__(self, k: _KT) -> None:
        del self._mapping[k]

    def __len__(self) -> int:
        return len(self._mapping)

    def __iter__(self) -> Iterator[_KT]:
        return iter(self._mapping)

    def __repr__(self):
        return f'Map({repr(self._mapping)})'


class MapField(FieldDescriptor[_VT], Generic[_KT, _VT]):
    repeated: bool = True
    key_type: Type[_KT]

    def __init__(self,
                 type_: Union[Type[_VT], str],
                 key_type: Type[_KT] = str,
                 name: str = None,
                 *,
                 json_name: str = None,
                 schema: 'venom.validation.Schema' = None,
                 **options) -> None:
        super(MapField, self).__init__(type_, name, json_name=json_name, schema=schema, options=options)
        self.key_type = key_type

    @overload
    def __get__(self, instance: None, owner) -> 'MapField[_VT]':
        pass

    @overload
    def __get__(self, instance: 'venom.message.Message', owner) -> Map[_KT, _VT]:
        pass

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return Map(instance, self.name)


def repeated(field: Union[FieldDescriptor, type, str], name: str = None) -> RepeatField:
    if isinstance(field, type) and issubclass(field, Field):
        field = field()
    elif not isinstance(field, FieldDescriptor):
        field = Field(field)

    if field.repeated:
        raise ValueError('Repeated fields cannot be embedded by another repeated field')

    return RepeatField(field._type,
                       name,
                       json_name=field.json_name,
                       schema=field.schema,
                       options=field.options)


def map_(field: Union[FieldDescriptor, type, str], key_type: Type[_KT] = str, name: str = None) -> MapField:
    if isinstance(field, type) and issubclass(field, Field):
        field = field()
    elif not isinstance(field, FieldDescriptor):
        field = Field(field)

    if field.repeated:
        raise ValueError('Repeated fields cannot be embedded by another repeated field')

    return MapField(field._type,
                    key_type,
                    name,
                    json_name=field.json_name,
                    schema=field.schema,
                    options=field.options)


def create_field_from_type_hint(hint,
                                converters: Sequence['venom.converter.Converter'] = (),
                                default: Any = None,
                                name: str = None,
                                *,
                                schema: 'venom.validator.Schema' = None):
    if hint in (bool, int, float, str, bytes):
        return Field(hint, default=default, name=name, schema=schema)

    for converter in converters:
        if converter.python == hint:
            return ConverterField(converter, name=name, schema=schema)

    # TODO type_ != Any is a workaround for https://github.com/python/typing/issues/345
    if hint != Any:
        if hasattr(hint, '__origin__') and hint.__origin__ is Repeat or issubclass(hint, List):
            return repeated(create_field_from_type_hint(hint.__args__[0], schema=schema), name=name)
        if hasattr(hint, '__origin__') and hint.__origin__ is Map:
            return map_(create_field_from_type_hint(hint.__args__[1], schema=schema), hint.__args__[0], name=name)

    from venom import Message
    # TODO type_ != Any is a workaround for https://github.com/python/typing/issues/345
    if hint != Any and issubclass(hint, Message):
        return Field(hint, name=name, schema=schema)

    raise NotImplementedError(f"Unable to generate field for {hint}")
