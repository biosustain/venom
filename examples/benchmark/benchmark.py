import timeit

from venom.message import Message
from venom.fields import String, Integer, Repeat


class PhoneNumber(Message):
    number = String()
    type = String() # choices.

class Person(Message):
    id = Integer()
    name = String() # min_length etc.
    email = String()
    phones = Repeat(PhoneNumber)

class AddressBook(Message):
    persons = Repeat(Person)

def test(setup, build, serialize, deserialize, number, entries, name):
    print('Testing {}: '.format(name))
    build = build.format(n=entries)
    build_times = timeit.repeat(repeat=1, number=number, stmt=build, setup=setup)
    print('{:<20} {:>6} ms'.format('build datastructure:', int(min(build_times) * 1000)))
    setup = setup + build
    serialize_times = timeit.repeat(repeat=1, number=number, stmt=serialize, setup=setup)
    print('{:<20} {:>6} ms'.format('serialize:', int(min(serialize_times) * 1000)))
    setup = setup + serialize
    deserialize_times = timeit.repeat(repeat=1, number=number, stmt=deserialize, setup=setup)
    print('{:<20} {:>6} ms'.format('deserialize:', int(min(deserialize_times) * 1000)))
    exec(setup)
    data_ = locals().get('data')
    total = int(1000 * sum([min(l) for l in [build_times, serialize_times, deserialize_times]]))
    print('{:<20} {:>6} ms'.format('totaltime:', total))
    print('{:<20} {:>6} MB\n'.format('size:', round(len(data_) / (1024*1024) * number, 2)))

setup = """\
import msgpack
"""
build = '''\
addresses = [{{
    'id': 123,
    'name': 'Alice',
    'email': 'alice@example.com',
    'phones': {{'number': "555-1212", 'type': 'mobile'}},
}} for _ in range({n})]
'''
serialize = '''\
data = msgpack.packb(addresses)
'''
deserialize = '''\
msgpack.unpackb(data)
'''
test(setup, build, serialize, deserialize, 1000, 100, 'Msgpack')



setup = """\
from venom.message import Message
from venom.fields import String, Integer, Repeat
from venom.serialization import JSON

class PhoneNumber(Message):
    number = String()
    type = String() # choices.

class Person(Message):
    id = Integer()
    name = String() # min_length etc.
    email = String()
    phones = Repeat(PhoneNumber)

class AddressBook(Message):
    persons = Repeat(Person)

wire_format = JSON()
"""

build = '''\
address_book = AddressBook()
address_book.persons = []

for i in range({n}):
  #person = address_book.persons.add()
  person = Person()
  address_book.persons.append(person)
  person.id = 123
  person.name = 'Alice'
  person.email ='alice@example.com'
  #phone_number = person.phone.add()
  phone_number = PhoneNumber()
  phone_number.number = "555-1212"
  # TODO support enum
  phone_number.type = "mobile"
  #phone_number.type = addressbook_pb2.Person.MOBILE
  person.phones = [phone_number]

'''
serialize = '''\
data = wire_format.pack(AddressBook, address_book)
'''
deserialize = '''\
wire_format.unpack(AddressBook, data)
'''
test(setup, build, serialize, deserialize, 1000, 100, 'Venom JSON (default)')


setup = """\
from venom.message import Message
from venom.fields import String, Integer, Repeat
from fast import FastJSON

class PhoneNumber(Message):
    number = String()
    type = String() # choices.

class Person(Message):
    id = Integer()
    name = String() # min_length etc.
    email = String()
    phones = Repeat(PhoneNumber)

class AddressBook(Message):
    persons = Repeat(Person)

wire_format = FastJSON()
"""

build = '''\
address_book = AddressBook()
address_book.persons = []

for i in range({n}):
  #person = address_book.persons.add()
  person = Person()
  address_book.persons.append(person)
  person.id = 123
  person.name = 'Alice'
  person.email ='alice@example.com'
  #phone_number = person.phone.add()
  phone_number = PhoneNumber()
  phone_number.number = "555-1212"
  # TODO support enum
  phone_number.type = "mobile"
  #phone_number.type = addressbook_pb2.Person.MOBILE
  person.phones = [phone_number]

'''
serialize = '''\
data = wire_format.pack(AddressBook, address_book)
'''
deserialize = '''\
wire_format.unpack(AddressBook, data)
'''
test(setup, build, serialize, deserialize, 1000, 100, 'Venom FastJSON')





setup = """\
from venom.message import Message
from venom.fields import String, Integer, Repeat
from fast import FastMsgPack

class PhoneNumber(Message):
    number = String()
    type = String() # choices.

class Person(Message):
    id = Integer()
    name = String() # min_length etc.
    email = String()
    phones = Repeat(PhoneNumber)

class AddressBook(Message):
    persons = Repeat(Person)

wire_format = FastMsgPack()
"""

build = '''\
address_book = AddressBook()
address_book.persons = []

for i in range({n}):
  #person = address_book.persons.add()
  person = Person()
  address_book.persons.append(person)
  person.id = 123
  person.name = 'Alice'
  person.email ='alice@example.com'
  #phone_number = person.phone.add()
  phone_number = PhoneNumber()
  phone_number.number = "555-1212"
  # TODO support enum
  phone_number.type = "mobile"
  #phone_number.type = addressbook_pb2.Person.MOBILE
  person.phones = [phone_number]

'''
serialize = '''\
data = wire_format.pack(AddressBook, address_book)
'''
deserialize = '''\
wire_format.unpack(AddressBook, data)
'''
test(setup, build, serialize, deserialize, 1000, 100, 'Venom Fast MsgPack')

setup = """
from venom.message import Message
from venom.fields import String, Integer, Repeat
from fast import FastMsgPack

class PhoneNumber(Message):
    number = String()
    type = String() # choices.

class Person(Message):
    id = Integer()
    name = String() # min_length etc.
    email = String()
    phones = Repeat(PhoneNumber)

class AddressBook(Message):
    persons = Repeat(Person)

wire_format = FastMsgPack()
"""
build = '''\
addresses = {{'persons': [{{
    'id': 123,
    'name': 'Alice',
    'email': 'alice@example.com',
    'phones': [{{'number': "555-1212", 'type': 'mobile'}}],
}} for _ in range({n})]}}

'''
serialize = '''\
data = wire_format.pack(AddressBook, addresses)
'''
deserialize = '''\
wire_format.unpack(AddressBook, data)
'''
test(setup, build, serialize, deserialize, 1000, 100, 'Venom Fast MsgPack from Python Dict')