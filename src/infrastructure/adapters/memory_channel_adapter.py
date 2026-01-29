"""
Adapter In-Memory du canal de messaging.

Utile pour les tests unitaires et le developpement sans Redis.
"""

import asyncio
import fnmatch
import logging
from typing import AsyncIterator, Dict, Any, List

from src.domain.ports.message_channel_port import Message, MessageChannel

logger = logging.getLogger(__name__)


class InMemoryMessageChannel(MessageChannel):
    """
    Canal de messages en memoire utilisant asyncio.Queue.

    Cette implementation est utile pour:
    - Les tests unitaires (pas de dependance externe)
    - Le developpement local sans Redis
    - Les scenarios mono-processus

    Note:
        Les messages ne sont pas persistes et sont perdus a la fermeture.
        Cette implementation est single-process uniquement.
    """

    def __init__(self):
        self._queue: asyncio.Queue[Message] = asyncio.Queue()
        self._patterns: List[str] = []
        self._connected = False

    async def connect(self) -> None:
        """Marque le canal comme connecte."""
        self._connected = True
        logger.info("Canal In-Memory connecte")

    async def disconnect(self) -> None:
        """Marque le canal comme deconnecte et vide la queue."""
        self._connected = False
        self._patterns = []

        # Vider la queue
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        logger.info("Canal In-Memory deconnecte")

    async def publish(self, channel: str, message: Dict[str, Any]) -> None:
        """
        Publie un message sur un canal.

        Le message est ajoute a la queue s'il correspond a un pattern abonne.

        Args:
            channel: Nom du canal
            message: Donnees a publier
        """
        if not self._connected:
            raise ConnectionError("Canal non connecte. Appelez connect() d'abord.")

        # Verifier si le canal correspond a un pattern abonne
        for pattern in self._patterns:
            if fnmatch.fnmatch(channel, pattern):
                msg = Message(
                    channel=channel,
                    data=message,
                    metadata={"pattern": pattern}
                )
                await self._queue.put(msg)
                return

    async def subscribe(self, pattern: str) -> None:
        """
        S'abonne a un pattern de canaux.

        Args:
            pattern: Pattern de canaux (ex: "inbox:*")
        """
        if not self._connected:
            raise ConnectionError("Canal non connecte. Appelez connect() d'abord.")

        if pattern not in self._patterns:
            self._patterns.append(pattern)
            logger.info(f"Abonne au pattern: {pattern}")

    async def listen(self) -> AsyncIterator[Message]:
        """
        Ecoute les messages sur les canaux abonnes.

        Yields:
            Message: Messages recus
        """
        if not self._connected:
            raise ConnectionError("Canal non connecte. Appelez connect() d'abord.")

        while self._connected:
            try:
                msg = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                yield msg
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    async def inject_message(self, channel: str, data: Dict[str, Any]) -> None:
        """
        Injecte directement un message dans la queue.

        Utile pour les tests sans passer par publish().

        Args:
            channel: Nom du canal
            data: Donnees du message
        """
        msg = Message(channel=channel, data=data, metadata={"injected": True})
        await self._queue.put(msg)
