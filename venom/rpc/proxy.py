from typing import Union, Type, TypeVar, Generic

from venom.rpc.service import Service


S = TypeVar('S', bound=Service)

class ServiceProxy(Generic[S]):
    # TODO define life-time. can be global or request or session.
    def __init__(self, reference: Union[str, Type[S]]) -> None:
        self.reference = reference

    def __get__(self, service: Service, owner) -> S:
        if service is None:
            return self  # XXX typing (descriptors not supported properly)
        else:
            return service.venom.get_instance(self.reference)
