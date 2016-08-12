

# TODO provided arguments.
# TODO resolvers/converters.
from typing import Tuple, Callable, Sequence, Dict

from venom.converter import Converter
from venom.message import Message


class Method(object):
    def __init__(self, fn, request, response):
        pass


def magic(fn: Callable,
          request: type(Message) = None,
          response: type(Message) = None,
          converters: Sequence[Converter] = None,
          context: Dict[type, str] = None) -> Tuple[type(Message), type(Message), Callable]:
    pass
