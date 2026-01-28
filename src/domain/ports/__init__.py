"""
Ports (Interfaces) - Contrats que les adapters doivent implémenter.

Les ports définissent les abstractions dont dépend la couche application.
Ils permettent l'inversion de dépendance (DIP - SOLID).
"""

from src.domain.ports.vector_store_port import VectorStorePort
from src.domain.ports.retriever_port import RetrieverPort

__all__ = ["VectorStorePort", "RetrieverPort"]
