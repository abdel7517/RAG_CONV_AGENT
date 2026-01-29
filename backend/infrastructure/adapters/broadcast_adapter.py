"""Adapter Redis pour le broker d'evenements via la lib broadcaster."""
from contextlib import asynccontextmanager

from broadcaster import Broadcast

from backend.domain.ports.event_broker_port import EventBrokerPort


class BroadcastEventBroker(EventBrokerPort):
    """
    Implementation du EventBrokerPort utilisant la lib broadcaster (Redis).

    Wrappe l'instance Broadcast pour respecter l'interface abstraite
    et masquer les details de la lib (event.message, etc.).
    """

    def __init__(self, url: str):
        self._broadcast = Broadcast(url)

    async def connect(self) -> None:
        await self._broadcast.connect()

    async def disconnect(self) -> None:
        await self._broadcast.disconnect()

    async def publish(self, channel: str, message: str) -> None:
        await self._broadcast.publish(channel=channel, message=message)

    @asynccontextmanager
    async def subscribe(self, channel: str):
        async with self._broadcast.subscribe(channel=channel) as subscriber:
            yield _BroadcastSubscription(subscriber)


class _BroadcastSubscription:
    """Wrapper autour du subscriber broadcaster pour exposer get() -> str."""

    def __init__(self, subscriber):
        self._subscriber = subscriber

    async def get(self) -> str:
        event = await self._subscriber.get()
        return event.message
