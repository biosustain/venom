from json import JSONDecodeError

from typing import Type, TypeVar

from venom import Message
from venom.common import FieldMask, StringValue, IntegerValue, NumberValue, BoolValue, Timestamp
from venom.exceptions import ValidationError
from .protocol import Protocol, TranscodingProtocol
from .transcode import JSONValueTranscoder, JSONTimestampTranscoder, JSONFieldMaskTranscoder, \
    URIStringDictMessageTranscoder

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

    def pack(self, message: Message) -> bytes:
        if self.is_empty:
            return b''
        return json.dumps(self.encode(message)).encode('utf-8')

    def unpack(self, buffer: bytes):
        # allow empty string when message is empty
        if len(buffer) == 0 and self.is_empty:
            return self.message()

        try:
            return self.decode(json.loads(buffer.decode('utf-8')))
        except (ValueError, JSONDecodeError) as e:
            raise ValidationError(f"Invalid JSONProtocol: {str(e)}")


class URIStringProtocol(TranscodingProtocol):
    mime = 'text/plain'
    name = 'uri-string'
    default_transcoder = URIStringDictMessageTranscoder


for protocol in (JSONProtocol, URIStringProtocol):
    for message in (StringValue, IntegerValue, NumberValue, BoolValue):
        JSONValueTranscoder.set_protocol_default(JSONProtocol, message)

    JSONTimestampTranscoder.set_protocol_default(JSONProtocol, Timestamp)
    JSONFieldMaskTranscoder.set_protocol_default(JSONProtocol, FieldMask)
