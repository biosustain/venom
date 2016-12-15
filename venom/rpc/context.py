from venom.rpc.resolver import Resolver


class RequestContext(object):
    pass


class RequestContextResolver(Resolver):
    python = RequestContext

    async def resolve(self,
                      service: 'venom.rpc.service.Service',
                      request: 'venom.message.Message') -> RequestContext:
        return service.context
