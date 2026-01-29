"""
Adapter Redis du canal de messaging.

Utilise redis.asyncio pour une communication Pub/Sub asynchrone.
"""

import json
import logging
from typing import AsyncIterator, Dict, Any, Optional

import redis.asyncio as redis

from src.domain.ports.message_channel_port import Message, MessageChannel

logger = logging.getLogger(__name__)


class RedisMessageChannel(MessageChannel):
    """
    Canal de messages utilisant Redis Pub/Sub.

    Cette implementation permet la communication entre plusieurs
    processus/services via Redis.

    Args:
        url: URL de connexion Redis (ex: "redis://localhost:6379")
    """

    def __init__(self, url: str = "redis://localhost:6379"):
        self.url = url
        self._redis: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        self._subscribed = False

    async def connect(self) -> None:
        """Etablit la connexion a Redis."""
        if self._redis is not None:
            return

        try:
            self._redis = redis.from_url(self.url)
            await self._redis.ping()
            logger.info(f"Connecte a Redis: {self.url}")
        except redis.ConnectionError as e:
            raise ConnectionError(f"Impossible de se connecter a Redis: {e}")

    async def disconnect(self) -> None:
        """Ferme la connexion a Redis."""
        if self._pubsub:
            try:
                await self._pubsub.unsubscribe()
            except Exception:
                pass
            self._pubsub = None

        if self._redis:
            try:
                await self._redis.close()
            except Exception:
                pass
            self._redis = None

        self._subscribed = False
        logger.info("Deconnecte de Redis")

    async def publish(self, channel: str, message: Dict[str, Any]) -> None:
        """
        Publie un message sur un canal Redis.

        Args:
            channel: Nom du canal
            message: Donnees a publier (sera serialise en JSON)
        """
        if self._redis is None:
            raise ConnectionError("Canal non connecte. Appelez connect() d'abord.")

        payload = json.dumps(message)
        await self._redis.publish(channel, payload)

    async def subscribe(self, pattern: str) -> None:
        """
        S'abonne a un pattern de canaux Redis.

        Args:
            pattern: Pattern de canaux (ex: "inbox:*")
        """
        if self._redis is None:
            raise ConnectionError("Canal non connecte. Appelez connect() d'abord.")

        self._pubsub = self._redis.pubsub()
        await self._pubsub.psubscribe(pattern)
        self._subscribed = True
        logger.info(f"Abonne au pattern: {pattern}")

    async def listen(self) -> AsyncIterator[Message]:
        """
        Ecoute les messages sur les canaux abonnes.

        Yields:
            Message: Messages recus avec les donnees parsees du JSON
        """
        if self._pubsub is None or not self._subscribed:
            raise ConnectionError("Pas d'abonnement actif. Appelez subscribe() d'abord.")

        async for raw_message in self._pubsub.listen():
            if raw_message["type"] == "pmessage":
                try:
                    data = json.loads(raw_message["data"])
                    channel = raw_message["channel"]
                    if isinstance(channel, bytes):
                        channel = channel.decode("utf-8")

                    yield Message(
                        channel=channel,
                        data=data,
                        metadata={
                            "pattern": raw_message.get("pattern"),
                            "type": raw_message.get("type")
                        }
                    )
                except json.JSONDecodeError as e:
                    logger.warning(f"Message JSON invalide: {e}")
                except Exception as e:
                    logger.error(f"Erreur lors du traitement du message: {e}")
