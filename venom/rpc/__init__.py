from typing import Iterable, Union, Tuple
from weakref import WeakKeyDictionary

from venom.rpc.remote import Remote
from venom.rpc.service import Service


class UnknownService(ValueError):
    pass


class RequestContext(object):
    pass


class Venom(object):
    def __init__(self):
        self._instances = WeakKeyDictionary()
        self._services = {}
        self._clients = {}

        # if schema is None:
        #     pass
        #     #from venom-1.schema.openapi import OpenAPISchema
        #     #schema = OpenAPISchema()
        # self.schema = schema

    # TODO change signature so that all keyword arguments go to the client_cls on init.
    def add(self, service: type(Service), client: 'venom.rpc.comms.BaseClient' = None) -> None:
        name = service.__meta__.name
        if name in self._services:
            if self._services[name] is service:
                return
            raise ValueError("A service is already defined under the name '{}'".format(name))
        self._services[name] = service
        self._clients[service] = client

    def _resolve_service_cls(self, reference: Union[str, type(Service)]):
        if isinstance(reference, str):
            try:
                return self._services[reference]
            except KeyError:
                raise UnknownService("No service named '{}' is known to this venom".format(reference))
        elif reference not in self._services.values():
            raise UnknownService("'{}' is not known to this venom".format(reference))
        return reference

    def get_instance(self, reference: Union[str, type], context: RequestContext = None):
        cls = self._resolve_service_cls(reference)

        if context:
            try:
                return self._instances[context][cls]
            except KeyError:
                pass
        else:
            context = RequestContext()

        if issubclass(cls, Remote):
            instance = cls(self._clients[cls], venom=self, context=context)
        else:
            instance = cls(venom=self, context=context)

        if context:
            if context in self._instances:
                self._instances[context][cls] = instance
            else:
                self._instances[context] = {cls: instance}
        return instance

    def iter_methods(self) -> Iterable[Tuple[type(Service), 'venom.rpc.method.BaseMethod']]:
        for service in self._services.values():
            if isinstance(service, Remote):
                continue

            for rpc in service.__methods__.values():
                yield service, rpc

    def __iter__(self) -> Iterable[type(Service)]:
        return iter(self._services.values())

