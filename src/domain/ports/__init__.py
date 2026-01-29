"""
Ports (Interfaces) - Contrats que les adapters doivent implémenter.

Les ports définissent les abstractions dont dépend la couche application.
Ils permettent l'inversion de dépendance (DIP - SOLID).
"""

from src.domain.ports.vector_store_port import VectorStorePort
from src.domain.ports.retriever_port import RetrieverPort
from src.domain.ports.llm_port import LLMPort
from src.domain.ports.document_loader_port import DocumentLoaderPort
from src.domain.ports.message_channel_port import MessageChannel, Message

__all__ = ["VectorStorePort", "RetrieverPort", "LLMPort", "DocumentLoaderPort", "MessageChannel", "Message"]
