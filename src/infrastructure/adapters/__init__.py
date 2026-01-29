"""
Adapters - Implémentations concrètes des ports.

Les adapters font le pont entre les abstractions du domain
et les technologies concrètes (PGVector, LangChain, Ollama, Mistral, OpenAI, etc.).
"""

from src.infrastructure.adapters.pgvector_adapter import PGVectorAdapter
from src.infrastructure.adapters.document_loader_adapter import PDFDocumentLoaderAdapter
from src.infrastructure.adapters.redis_channel_adapter import RedisMessageChannel
from src.infrastructure.adapters.memory_channel_adapter import InMemoryMessageChannel
from src.infrastructure.adapters.ollama_adapter import OllamaAdapter
from src.infrastructure.adapters.mistral_adapter import MistralAdapter
from src.infrastructure.adapters.openai_adapter import OpenAIAdapter

__all__ = [
    "PGVectorAdapter",
    "PDFDocumentLoaderAdapter",
    "RedisMessageChannel",
    "InMemoryMessageChannel",
    "OllamaAdapter",
    "MistralAdapter",
    "OpenAIAdapter",
]
