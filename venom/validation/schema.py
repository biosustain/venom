from typing import ClassVar, Mapping, Union, Type, List

from venom import Message
from venom.common import NumberValue, IntegerValue, Value
from venom.common.types import JSONValue
from venom.fields import repeated, Map, Field


class Schema(Message):
    __python_type_schemas: ClassVar[Mapping[type, 'Schema']] = {}

    minimum: NumberValue
    maximum: NumberValue

    exclusive_minimum: bool
    exclusive_maximum: bool

    min_length: int
    max_length: IntegerValue

    pattern: str

    min_items: int
    max_items: IntegerValue
    unique_items: bool

    min_properties: int
    max_properties: IntegerValue

    enum: List[Value]

    multiple_of: float

    @classmethod
    def register(cls, target: Type[Union[str, int, float, bool, list, dict]], **kwargs) -> None:
        """
        
        Example usage:::
    
            Password = NewType('Password', str)
            Schema.register(Password, min_length=8, max_length=10)

        :param target: 
        :param kwargs: 
        :return: 
        """
        if target in (str, int, float, bool, list, dict):
            raise ValueError('Schemas must not be applied to built-in types; target must subclass a built-in type.')

        if target in cls.__python_type_schemas[target]:
            # TODO warning or error here.
            cls.__python_type_schemas[target].update(**kwargs)
        else:
            cls.__python_type_schemas[target] = Schema(**kwargs)

    @classmethod
    def lookup(cls, target: Type[Union[str, int, float, bool, list, dict]]) -> 'Schema':
        try:
            return cls.__python_type_schemas[target]
        except KeyError:
            return Schema()


def schema(name: str, **kwargs):
    """

    Example usage:::

        @rpc(auto=True)
        @schema('name', min_length=5)
        def say_hello(self, name: str):
            pass

    :param name: 
    :param kwargs: 
    :return: 
    """
    def decorator(func):
        return func
    return decorator
