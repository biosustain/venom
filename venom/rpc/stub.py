from venom.rpc.service import Service, ServiceMeta


class StubMeta(ServiceMeta):
    def __new__(metacls, what, bases=None, members=None):
        cls = super().__new__(metacls, what, bases, members)
        cls.__methods__ = {
            name: method.stub(cls, name)
            for name, method in cls.__methods__.items()
        }
        return cls


class Stub(Service, metaclass=StubMeta):
    pass
