"""
Adapters - Implémentations concrètes des ports.

Les adapters font le pont entre les abstractions du domain
et les technologies concrètes (PGVector, LangChain, etc.).
"""

from src.infrastructure.adapters.pgvector_adapter import PGVectorAdapter
from src.infrastructure.adapters.langchain_retriever_adapter import LangChainRetrieverAdapter

__all__ = ["PGVectorAdapter", "LangChainRetrieverAdapter"]
