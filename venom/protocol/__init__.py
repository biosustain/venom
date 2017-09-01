from json import JSONDecodeError

from typing import Type, TypeVar

from venom import Message
from venom.common import FieldMask, StringValue, IntegerValue, NumberValue, BoolValue, Timestamp, JSONValue
from venom.exceptions import ValidationError
from .protocol import Protocol, TranscodingProtocol
from .transcode import JSONValueTranscoder, JSONTimestampTranscoder, JSONFieldMaskTranscoder, \
    URIStringDictMessageTranscoder, JSONTranscoder

_M = TypeVar('M', bound=Message)

try:
    import ujson as json
except ImportError:
    import json


class JSONProtocol(TranscodingProtocol):
    mime = 'application/json'
    name = 'json'

    def __init__(self, message: Type[Message], field_mask: FieldMask = None):
        super().__init__(message, field_mask)

        self.is_empty = len(message.__fields__) == 0 or self.field_mask and len(self.field_mask.paths) == 0

    def packs(self, message: Message) -> str:
        if self.is_empty:
            return ''
        return json.dumps(self.encode(message))

    def unpacks(self, buffer: str) -> Message:
        # allow empty string when message is empty
        if len(buffer) == 0 and self.is_empty:
            return self.message()

        try:
            return self.decode(json.loads(buffer))
        except (ValueError, JSONDecodeError) as e:
            raise ValidationError(f"Invalid JSONProtocol: {str(e)}")

    def pack(self, message: Message) -> bytes:
        return self.packs(message).encode('utf-8')

    def unpack(self, buffer: bytes) -> Message:
        return self.unpacks(buffer.decode('utf-8'))


class URIStringProtocol(TranscodingProtocol):
    mime = 'text/plain'
    name = 'uri-string'
    default_transcoder = URIStringDictMessageTranscoder


for protocol in (JSONProtocol, URIStringProtocol):
    for message in (StringValue, IntegerValue, NumberValue, BoolValue):
        JSONValueTranscoder.set_protocol_default(JSONProtocol, message)

    JSONTranscoder.set_protocol_default(JSONProtocol, JSONValue)
    JSONTimestampTranscoder.set_protocol_default(JSONProtocol, Timestamp)
    JSONFieldMaskTranscoder.set_protocol_default(JSONProtocol, FieldMask)
