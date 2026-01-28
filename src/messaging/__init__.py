"""
Module de messaging abstrait pour le projet RAG Conversational Agent.

Ce module fournit une couche d'abstraction pour les canaux de communication,
permettant d'utiliser differents backends (Redis, In-Memory, etc.) de maniere
transparente.
"""

from .base import Message, MessageChannel
from .redis_channel import RedisMessageChannel
from .memory_channel import InMemoryMessageChannel
from .factory import create_channel

__all__ = [
    "Message",
    "MessageChannel",
    "RedisMessageChannel",
    "InMemoryMessageChannel",
    "create_channel",
]
