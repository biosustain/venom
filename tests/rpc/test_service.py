from venom import Empty
from venom.common import StringValue
from venom.rpc import RequestContext, Venom
from venom.rpc import rpc, Service
from venom.rpc.test_utils import AioTestCase


class ServiceTestCase(AioTestCase):
    def test_service_methods(self):
        class PetService(Service):
            @rpc
            def pet(self) -> None:
                pass

        self.assertEqual(set(PetService.__methods__.keys()), {"pet"})

    def test_service_methods_inheritance(self):
        class PetService(Service):
            @rpc
            def pet(self) -> None:
                pass

        class SnakeService(PetService):
            @rpc
            def boop(self) -> None:
                pass

        self.assertEqual(set(SnakeService.__methods__.keys()), {"pet", "boop"})

    async def test_request_context(self):
        class SnakeService(Service):
            @rpc
            def sound(self) -> str:
                return self.context.get('sound', 'silence')

        venom = Venom()
        venom.add(SnakeService)

        self.assertEqual(await venom.invoke(SnakeService().sound, Empty()), StringValue('silence'))

        @Venom.before_invoke.connect_via(venom, weak=True)
        def set_context_sound(sender, **kwargs):
            RequestContext.current()['sound'] = 'hiss'

        self.assertEqual(await venom.invoke(SnakeService().sound, Empty()), StringValue('hiss'))
