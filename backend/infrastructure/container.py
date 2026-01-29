"""
Container DI declaratif pour le backend FastAPI.

Utilise dependency-injector pour le wiring automatique avec @inject,
comme dans src/infrastructure/container.py.

Documentation: https://python-dependency-injector.ets-labs.org/
"""

from dependency_injector import containers, providers

from src.config import settings
from backend.infrastructure.adapters.broadcast_adapter import BroadcastEventBroker


class Container(containers.DeclarativeContainer):
    """
    Container DI du backend.

    Usage Production:
        container = Container()
        broker = container.event_broker()

    Usage Tests (override sans modifier le code):
        with container.event_broker.override(mock_broker):
            # Les routes utilisent le mock
    """

    wiring_config = containers.WiringConfiguration(
        modules=["backend.routes.chat", "backend.routes.stream"]
    )

    # =========================================================================
    # EVENT BROKER
    # =========================================================================

    event_broker = providers.Singleton(
        BroadcastEventBroker,
        url=settings.REDIS_URL,
    )
    """
    Broker d'evenements (Singleton).
    Une seule connexion Redis partagee par toute l'application.
    """
