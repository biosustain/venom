from abc import ABCMeta
from collections import Mapping, ItemsView
from collections import OrderedDict

from typing import Any, Dict, Type, Iterable, TypeVar, ClassVar, cast, get_type_hints, Tuple

from venom.fields import FieldDescriptor, create_field_from_type_hint
from venom.util import meta


class OneOf(object):
    def __init__(self, *choices):
        self.choices = choices

    # TODO helper functions.

    def which(self):
        raise NotImplementedError

    def get(self) -> Any:
        raise NotImplementedError


class MessageMeta(ABCMeta):
    @classmethod
    def __prepare__(metacls, name, bases):
        return OrderedDict()

    def __new__(metacls, name, bases, members):
        cls = super(MessageMeta, metacls).__new__(metacls, name, bases, members)
        cls.__fields__ = OrderedDict(getattr(cls, '__fields__') or ())
        cls.__meta__, meta_changes = meta(bases, members)
        cls.__meta__.protocols = {}
        cls.__meta__.validators = {}

        if not meta_changes.get('name', None):
            cls.__meta__.name = name


        # FIXME support self-referential type hints
        for name, hint in cls.__annotations__.items():
            if not name.startswith('_'):
                field_descriptor = create_field_from_type_hint(hint, name=name)
                setattr(cls, name, field_descriptor)
                members[name] = field_descriptor

        for name, member in members.items():
            if isinstance(member, FieldDescriptor):
                cls.__fields__[member.name] = member
            elif isinstance(member, OneOf):
                cls.__meta__.one_of_groups += (name, member.choices)

        return cls


class Message(Mapping, metaclass=MessageMeta):
    __slots__ = ('_values',)  # TODO slot message fields directly.
    # TODO change to tuple (FieldDescriptor would need FieldDescriptor.attribute attribute.)
    __fields__: ClassVar[Dict[str, FieldDescriptor]] = None
    __meta__: ClassVar[Dict[str, Any]] = None

    class Meta:
        name = None
        one_of_groups = ()
        protocols = None
        validators = None

    def __init__(self, *args, **kwargs):
        self._values = {}
        if args:
            for value, field in zip(args, self.__fields__.values()):
                if value is not None:
                    field.__set__(self, value)
        for key, value in kwargs.items():
            if value is not None:
                self.__fields__[key].__set__(self, value)

    def get(self, key, default=None):
        try:
            return self._values[key]
        except KeyError:
            if default is None and key in self.__fields__:
                return self.__fields__[key].default()
            return default

    def __getitem__(self, key):
        return self._values[key]

    def __setitem__(self, key, value):
        if value is None:
            try:
                del self._values[key]
            except KeyError:
                pass
        else:
            self._values[key] = value

    def __delitem__(self, key):
        del self._values[key]

    def __contains__(self, key):
        return key in self._values

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def __repr__(self):
        parts = []
        for key in self.__fields__.keys():
            if key in self._values and self._values[key] is not None:
                parts.append('{}={}'.format(key, repr(self._values[key])))
        return '{}({})'.format(self.__meta__.name, ', '.join(parts))

    def __eq__(self, other):
        if not isinstance(other, (Message, Mapping)):
            return NotImplemented
        return dict(ItemsView(self)) == dict(ItemsView(other))


def items(message: Message) -> ItemsView:
    return ItemsView(message)


def fields(message: Type[Message]) -> Iterable[FieldDescriptor]:
    return tuple(message.__fields__.values())


def field_names(message: Type[Message]) -> Iterable[str]:
    return tuple(field.name for field in message.__fields__.values())


_M = TypeVar('M', bound=Message)


def merge_into(message: _M, *others: _M):
    for other in others:
        for name, value in items(other):
            message[name] = value
    return message


def is_empty(message: Type[Message]) -> bool:
    return not fields(message)


def from_object(message: Type[_M], obj: Any) -> _M:
    kwargs = {}

    for name in message.__fields__.keys():
        if hasattr(obj, '__getitem__'):
            # TODO skip None values
            try:
                kwargs[name] = obj[name]
                continue
            except (IndexError, TypeError, KeyError):
                pass
        try:
            kwargs[name] = getattr(obj, name)
        except AttributeError:
            pass

    return message(**kwargs)


def to_dict(message: Message, dict_cls: type = dict):
    return dict_cls(items(message))


def one_of(*choices):
    """

    Usage:::

        class SearchRequest(Message):
            query = one_of('name', 'id')

        s = SearchRequest(id=123)
        s.query.which()  # 'id'


    """
    return OneOf(choices)


class Empty(Message):
    pass


def message_factory(name: str, fields: Dict[str, FieldDescriptor], *, super_message: Type[_M] = Message) -> Type[_M]:
    return cast(Type[_M], type(name, (super_message,), fields))
