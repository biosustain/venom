import msgpack
from venom.message import Message
from venom.serialization import JSON


class MsgPack(JSON):
    mime = 'application/msgpack'

    def pack(self, fmt: type(Message), message: Message) -> bytes:
        return msgpack.packb(self.encode(message, cls=fmt), use_bin_type=True)

    def unpack(self, fmt: type(Message), value: bytes):
        # TODO catch JSONDecodeError
        return self.decode(msgpack.unpackb(value, encoding='utf-8'), cls=fmt)