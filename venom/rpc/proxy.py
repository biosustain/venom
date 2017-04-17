from typing import Union, Type, TypeVar, Generic, cast, Any

from venom.rpc.service import Service

S = TypeVar('S', bound=Service)


class ServiceProxy(Generic[S]):
    # TODO define life-time. can be global or request or session.
    def __init__(self, reference: Union[str, Type[S]]) -> None:
        self.reference = reference

    def __get__(self, service: Service, owner: Any = None) -> S:
        return cast(S, service.venom.get_instance(self.reference))


def proxy(service: Type[S]) -> S:
    return cast(S, ServiceProxy(service))
