"""
Port (Interface) pour les canaux de messaging.

Ce port definit le contrat que toutes les implementations
de canaux doivent respecter (Redis, In-Memory, Kafka, etc.).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, Dict, Any, Optional


@dataclass
class Message:
    """
    Message standardise pour tous les canaux.

    Attributes:
        channel: Nom du canal sur lequel le message a ete recu
        data: Donnees du message (dict JSON-serializable)
        metadata: Metadonnees optionnelles (timestamp, source, etc.)
    """
    channel: str
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


class MessageChannel(ABC):
    """
    Interface abstraite pour un canal de messages.

    Implementations possibles:
    - RedisMessageChannel (Redis Pub/Sub)
    - InMemoryMessageChannel (asyncio.Queue, pour tests/dev)
    """

    @abstractmethod
    async def connect(self) -> None:
        """
        Etablit la connexion au canal.

        Raises:
            ConnectionError: Si la connexion echoue
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Ferme la connexion au canal.

        Cette methode doit etre appellee pour liberer les ressources.
        """
        pass

    @abstractmethod
    async def publish(self, channel: str, message: Dict[str, Any]) -> None:
        """
        Publie un message sur un canal.

        Args:
            channel: Nom du canal de destination
            message: Donnees a publier (dict JSON-serializable)

        Raises:
            ConnectionError: Si le canal n'est pas connecte
        """
        pass

    @abstractmethod
    async def subscribe(self, pattern: str) -> None:
        """
        S'abonne a un pattern de canaux.

        Args:
            pattern: Pattern de canaux (ex: "inbox:*" pour tous les inbox)

        Raises:
            ConnectionError: Si le canal n'est pas connecte
        """
        pass

    @abstractmethod
    def listen(self) -> AsyncIterator[Message]:
        """
        Ecoute les messages entrants sur les canaux abonnes.

        Yields:
            Message: Messages recus sur les canaux abonnes

        Raises:
            ConnectionError: Si le canal n'est pas connecte ou abonne
        """
        pass

    async def __aenter__(self):
        """Context manager: connexion automatique."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager: deconnexion automatique."""
        await self.disconnect()
