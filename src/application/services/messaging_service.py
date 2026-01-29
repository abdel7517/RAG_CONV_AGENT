"""
Service de messaging encapsulant la logique de canaux.

Ce service abstrait les détails d'implémentation (patterns, préfixes, format)
pour que l'appelant puisse simplement publish/listen sans se soucier de la config.
"""

import logging
from typing import AsyncIterator

from src.domain.ports.message_channel_port import MessageChannel, Message

logger = logging.getLogger(__name__)


class MessagingService:
    """
    Service de messaging qui encapsule la logique de canaux.

    L'appelant n'a pas besoin de connaître:
    - Les patterns (inbox:*, outbox:)
    - La connexion/déconnexion
    - Le format des messages

    Usage:
        async with messaging_service as messaging:
            async for msg in messaging.listen():
                await messaging.publish_chunk(email, "Hello")
                await messaging.publish_chunk(email, "", done=True)
    """

    INBOX_PATTERN = "inbox:*"
    OUTBOX_PREFIX = "outbox:"

    def __init__(self, channel: MessageChannel):
        """
        Initialise le service avec un canal de messaging.

        Args:
            channel: Canal de messaging injecté (Redis ou InMemory)
        """
        self._channel = channel
        self._connected = False

    async def start(self) -> None:
        """
        Connecte et s'abonne aux messages entrants.

        Cette méthode est appelée automatiquement via le context manager.
        """
        logger.info(f"Démarrage du MessagingService sur {self.INBOX_PATTERN}...")
        await self._channel.connect()
        await self._channel.subscribe(self.INBOX_PATTERN)
        self._connected = True
        logger.info("MessagingService connecté et en écoute")

    async def stop(self) -> None:
        """
        Déconnecte proprement du canal.

        Cette méthode est appelée automatiquement via le context manager.
        """
        if self._connected:
            logger.info("Arrêt du MessagingService...")
            await self._channel.disconnect()
            self._connected = False
            logger.info("MessagingService déconnecté")

    def listen(self) -> AsyncIterator[Message]:
        """
        Écoute les messages entrants.

        Yields:
            Message: Messages reçus sur le canal inbox

        Raises:
            ConnectionError: Si le service n'est pas connecté
        """
        if not self._connected:
            raise ConnectionError("MessagingService non connecté. Utilisez 'async with' ou appelez start().")
        return self._channel.listen()

    async def publish_chunk(self, email: str, chunk: str, done: bool = False) -> None:
        """
        Publie un chunk de réponse vers l'utilisateur.

        Args:
            email: Email de l'utilisateur (identifiant du canal de sortie)
            chunk: Contenu du chunk à envoyer
            done: True si c'est le dernier chunk de la réponse
        """
        outbox = f"{self.OUTBOX_PREFIX}{email}"
        await self._channel.publish(outbox, {"chunk": chunk, "done": done})

        if done:
            logger.debug(f"Réponse complète envoyée à {email}")

    async def publish_error(self, email: str, error: str) -> None:
        """
        Publie une erreur vers l'utilisateur.

        Args:
            email: Email de l'utilisateur
            error: Message d'erreur à envoyer
        """
        logger.error(f"Erreur pour {email}: {error}")
        await self.publish_chunk(email, f"Erreur: {error}", done=True)

    async def __aenter__(self) -> "MessagingService":
        """Context manager: connexion automatique."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager: déconnexion automatique."""
        await self.stop()
