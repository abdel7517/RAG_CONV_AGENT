"""
Factory pour creer des canaux de messaging.

Permet d'instancier le bon type de canal en fonction de la configuration.
"""

from typing import Optional

from .base import MessageChannel
from .redis_channel import RedisMessageChannel
from .memory_channel import InMemoryMessageChannel


def create_channel(
    channel_type: str,
    url: Optional[str] = None,
    **kwargs
) -> MessageChannel:
    """
    Cree un canal de messaging du type specifie.

    Args:
        channel_type: Type de canal ("redis", "memory")
        url: URL de connexion (requis pour redis)
        **kwargs: Arguments supplementaires pour le canal

    Returns:
        MessageChannel: Instance du canal configure

    Raises:
        ValueError: Si le type de canal est inconnu

    Examples:
        >>> channel = create_channel("redis", url="redis://localhost:6379")
        >>> channel = create_channel("memory")
    """
    channel_type = channel_type.lower()

    if channel_type == "redis":
        if url is None:
            url = "redis://localhost:6379"
        return RedisMessageChannel(url=url)

    elif channel_type in ("memory", "in-memory", "inmemory"):
        return InMemoryMessageChannel()

    else:
        supported = ["redis", "memory"]
        raise ValueError(
            f"Type de canal inconnu: '{channel_type}'. "
            f"Types supportes: {', '.join(supported)}"
        )
