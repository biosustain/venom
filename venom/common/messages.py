from venom.fields import String
from venom.message import Message


class Date(Message):
    value = String(format='date')


class DateTime(Message):
    value = String(format='date-time')


class Empty(Message):
    pass


# class Any(Message):
#     type = String()
#     value =
# value could be struct; or string (bytes). Depends on implementation
