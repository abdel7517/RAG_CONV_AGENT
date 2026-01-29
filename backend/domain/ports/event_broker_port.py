"""Port abstrait pour le broker d'evenements (pub/sub)."""
from abc import ABC, abstractmethod
from typing import AsyncContextManager, Protocol, runtime_checkable


@runtime_checkable
class Subscription(Protocol):
    """Protocol pour les abonnements supportant get() asynchrone."""
    async def get(self) -> str: ...


class EventBrokerPort(ABC):
    """
    Interface abstraite pour un broker d'evenements pub/sub.

    Permet de publier des messages sur des canaux et de s'y abonner.
    L'implementation concrete (Redis, In-Memory, etc.) est injectee
    via FastAPI Depends().
    """

    @abstractmethod
    async def connect(self) -> None:
        """Etablit la connexion au broker."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Ferme la connexion au broker."""
        ...

    @abstractmethod
    async def publish(self, channel: str, message: str) -> None:
        """Publie un message sur un canal."""
        ...

    @abstractmethod
    def subscribe(self, channel: str) -> AsyncContextManager[Subscription]:
        """Retourne un context manager pour s'abonner a un canal."""
        ...
