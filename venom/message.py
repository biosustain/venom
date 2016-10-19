from abc import ABCMeta
from collections import MutableMapping
from collections import OrderedDict
from typing import Any, Dict, Type

from venom.fields import Field, FieldDescriptor
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
    def __prepare__(mcs, name, bases):
        return OrderedDict()

    def __new__(mcs, name, bases, members):
        cls = super(MessageMeta, mcs).__new__(mcs, name, bases, members)
        cls.__fields__ = OrderedDict(getattr(cls, '__fields__') or ())
        cls.__meta__, meta_changes = meta(bases, members)
        cls.__meta__.wire_formats = {}

        if not meta_changes.get('name', None):
            cls.__meta__.name = name

        for name, member in members.items():
            if isinstance(member, FieldDescriptor):
                cls.__fields__[name] = member
                if member.attribute is None:
                    member.attribute = name
            elif isinstance(member, OneOf):
                cls.__meta__.one_of_groups += (name, member.choices)

        return cls


class Message(MutableMapping, metaclass=MessageMeta):
    __slots__ = ('_values',)
    __fields__ = None  # type: Dict[str, Field]
    __meta__ = None  # type: Dict[str, Any]

    class Meta:
        name = None
        one_of_groups = ()
        wire_formats = None

    def __init__(self, *args, **kwargs):
        if args:
            self._values = {}
            for value, key in zip(args, self.__fields__.keys()):
                self._values[self.__fields__[key].attribute] = value
            for key, value in kwargs.items():
                self._values[self.__fields__[key].attribute] = value
        else:
            self._values = {self.__fields__[key].attribute: value for key, value in kwargs.items()}

    @classmethod
    def from_object(cls, obj):
        kwargs = {}

        for key, field in cls.__fields__.items():
            if hasattr(obj, '__getitem__'):
                try:
                    kwargs[key] = obj[key]
                    continue
                except (IndexError, TypeError, KeyError):
                    pass
            try:
                kwargs[key] = getattr(obj, key)
            except AttributeError:
                pass

        return cls(**kwargs)

    def __getitem__(self, key):
        return self._values[key]

    def __setitem__(self, key, value):
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
        for key, fields in self.__fields__.items():
            if fields.attribute in self._values:
                parts.append('{}={}'.format(key, repr(self._values[fields.attribute])))

        return '{}({})'.format(self.__meta__.name, ', '.join(parts))


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


def get_or_default(message: Message, key: str, default: Any = None):
    try:
        return message[key]
    except KeyError as e:
        if key in message.__fields__:
            if default is None:
                return message.__fields__[key].default()
            return default
        raise e
