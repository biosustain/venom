from venom.fields import String, Number, Int32, Integer
from venom.message import Message, one_of


class Date(Message):
    value = String(format='date')


class DateTime(Message):
    value = String(format='date-time')



# class Any(Message):
#     type = String()
#     value =
# value could be struct; or string (bytes). Depends on implementation


class IntegerValue(Message):
    value = Integer()


class Int32Value(Message):
    value = Int32()


class Value(Message):
    value = one_of(
        number_value=Number(),
        string_value=String(),
        # bool_value=Boolean()
        # TODO
    )


