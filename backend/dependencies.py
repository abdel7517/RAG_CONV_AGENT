"""Dependencies partagees pour l'API — resolution des ports."""
import os

from backend.domain.ports.event_broker_port import EventBrokerPort
from backend.infrastructure.adapters.broadcast_adapter import BroadcastEventBroker

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

_event_broker: EventBrokerPort = BroadcastEventBroker(REDIS_URL)


def get_event_broker() -> EventBrokerPort:
    """Fournit le broker d'evenements pour FastAPI Depends()."""
    return _event_broker
