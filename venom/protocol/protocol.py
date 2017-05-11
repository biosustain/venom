from abc import ABC, abstractmethod, ABCMeta

from typing import ClassVar, Type, Any, Union, Set

from venom import Message
from venom.common import FieldMask
from venom.protocol.transcode import MessageTranscoder, DictMessageTranscoder, _Value


class Protocol(ABC):
    mime: ClassVar[str] = None
    name: ClassVar[str] = None

    message: Type[Message]

    def __init__(self, message: Type[Message]):
        self.message = message

    @abstractmethod
    def pack(self, obj: Any) -> bytes:
        pass

    @abstractmethod
    def unpack(self, buffer: bytes) -> Any:
        pass


class TranscodingProtocol(Protocol, metaclass=ABCMeta):
    default_transcoder: Type[MessageTranscoder] = DictMessageTranscoder
    field_mask: FieldMask = None

    def __init__(self, message: Type[Message], field_mask: Union[Set[str], FieldMask] = None):
        super().__init__(message)

        if field_mask and isinstance(field_mask, set):  # TODO emit deprecation warning
            field_mask = FieldMask(field_mask)

        self.is_empty = len(message.__fields__) == 0

        if field_mask:
            coder = self.default_transcoder.get(self.__class__, message)
            if not issubclass(coder, DictMessageTranscoder):
                raise ValueError(f'Unable to use "field_mask" argument with {message}')

            if len(field_mask.paths) == 0:
                self.is_empty = True

            self.field_mask = field_mask
            self.message_coder = coder(self.__class__, message, field_mask)
        else:
            self.message_coder = self.default_transcoder.get_instance(self.__class__, message)

    def encode(self, message: Message) -> _Value:
        return self.message_coder.encode(message)

    def decode(self, instance: _Value, message: Message = None) -> Message:
        return self.message_coder.decode(instance, message)
