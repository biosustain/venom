from abc import ABCMeta
from collections import MutableMapping
from collections import OrderedDict
from typing import Any, Dict, Type, Iterable, TypeVar, Tuple, Set, ClassVar

from venom.fields import FieldDescriptor
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

        if not meta_changes.get('name', None):
            cls.__meta__.name = name

        for name, member in members.items():
            if isinstance(member, FieldDescriptor):
                cls.__fields__[member.name] = member
            elif isinstance(member, OneOf):
                cls.__meta__.one_of_groups += (name, member.choices)

        return cls


class Message(MutableMapping, metaclass=MessageMeta):
    __slots__ = ('_values',)   # TODO slot message fields directly.
    # TODO change to tuple (FieldDescriptor would need FieldDescriptor.attribute attribute.)
    __fields__: ClassVar[Tuple[FieldDescriptor]] = None
    __meta__: ClassVar[Dict[str, Any]] = None

    class Meta:
        name = None
        one_of_groups = ()
        protocols = None

    def __init__(self, *args, **kwargs):
        if args:
            self._values = {}
            for value, key in zip(args, self.__fields__.keys()):
                self[key] = value
            for key, value in kwargs.items():
                self[key] = value
        else:
            self._values = {key: value for key, value in kwargs.items() if value is not None}

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
            if key in self._values:
                parts.append('{}={}'.format(key, repr(self._values[key])))
        return '{}({})'.format(self.__meta__.name, ', '.join(parts))


def fields(message: Type[Message]) -> Iterable[FieldDescriptor]:
    return tuple(message.__fields__.values())


def field_names(message: Type[Message]) -> Iterable[FieldDescriptor]:
    return tuple(field.name for field in message.__fields__.values())


_M = TypeVar('M', bound=Message)


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


def message_factory(name: str, fields: Dict[str, FieldDescriptor]) -> Type[Message]:
    return type(name, (Message,), fields)
