from typing import ClassVar, Mapping, Any, Union, Type

from venom import Message
from venom.fields import Integer


class Schema(Message):
    __python_type_schemas: ClassVar[Mapping[type, 'Schema']] = {}

    min_length = Integer()
    max_length = Integer()
    # TODO other schema parameters

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
            raise ValueError('Schemas must not be applied to built-in types.')

        if target in cls.__python_type_schemas[target]:
            # TODO warning or error here.
            cls.__python_type_schemas[target].update(**kwargs)
        else:
            cls.__python_type_schemas[target] = Schema(**kwargs)


def schema(name: str, **kwargs):
    """

    Example usage:::

        @rpc
        @schema('name', min_length=5)
        def say_hello(self, name: str):
            pass

    :param name: 
    :param kwargs: 
    :return: 
    """
    raise NotImplementedError
