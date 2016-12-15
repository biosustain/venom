from typing import Union, Type

from venom.rpc.service import Service


class ServiceProxy(object):
    # TODO define life-time. can be global or request or session.
    def __init__(self, reference: Union[str, type]) -> None:
        self.reference = reference

    def __get__(self, service: Service, owner) -> Service:
        if service is None:
            return self
        else:
            return service.venom.get_instance(self.reference, service.context)
