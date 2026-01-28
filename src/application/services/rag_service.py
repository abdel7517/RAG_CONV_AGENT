"""
RAGService - Service de recherche documentaire (Architecture Hexagonale).

Ce service dépend UNIQUEMENT des ports (interfaces), pas des implémentations
concrètes. L'injection de dépendances se fait via le Container.

Principe SOLID respecté:
- DIP (Dependency Inversion): Dépend des abstractions, pas des concretions
- SRP (Single Responsibility): Orchestration de la recherche RAG
- OCP (Open/Closed): Extensible via nouveaux adapters
"""

import logging
from typing import Optional, List, Tuple, Any

from src.domain.ports.retriever_port import RetrieverPort

logger = logging.getLogger(__name__)


class RAGService:
    """
    Service RAG avec injection de dépendances via INTERFACES.

    Ce service ne connaît que les ports (abstractions), pas les
    implémentations concrètes (PGVector, LangChain, etc.).

    Usage:
        # Via le Container (production)
        from src.infrastructure.container import Container
        service = Container.create_rag_service()

        # Via injection directe (tests)
        mock_retriever = Mock(spec=RetrieverPort)
        service = RAGService(retriever=mock_retriever)

        # Recherche
        docs = service.search("ma question", company_id="techstore")
    """

    def __init__(self, retriever: RetrieverPort):
        """
        Initialise le service RAG.

        Args:
            retriever: Port du retriever (interface, pas implémentation)
        """
        self._retriever = retriever
        logger.debug("RAGService initialisé (architecture hexagonale)")

    def search(
        self,
        query: str,
        company_id: Optional[str] = None,
        k: Optional[int] = None
    ) -> List[Any]:
        """
        Recherche des documents pertinents.

        Args:
            query: La requête de recherche
            company_id: Filtre par entreprise (multi-tenant)
            k: Nombre de résultats

        Returns:
            Liste des documents pertinents
        """
        logger.debug(f"RAGService.search: query='{query[:50]}...', company_id={company_id}")
        return self._retriever.retrieve(query, k=k, company_id=company_id)

    def search_formatted(
        self,
        query: str,
        company_id: Optional[str] = None,
        k: Optional[int] = None
    ) -> str:
        """
        Recherche et formate les résultats en string.

        Args:
            query: La requête de recherche
            company_id: Filtre par entreprise (multi-tenant)
            k: Nombre de résultats

        Returns:
            Chaîne formatée avec les documents pertinents
        """
        logger.debug(f"RAGService.search_formatted: query='{query[:50]}...', company_id={company_id}")
        return self._retriever.retrieve_formatted(query, k=k, company_id=company_id)

    def search_with_scores(
        self,
        query: str,
        company_id: Optional[str] = None,
        k: Optional[int] = None
    ) -> List[Tuple[Any, float]]:
        """
        Recherche avec scores de similarité.

        Args:
            query: La requête de recherche
            company_id: Filtre par entreprise
            k: Nombre de résultats

        Returns:
            Liste de tuples (Document, score)
        """
        logger.debug(f"RAGService.search_with_scores: query='{query[:50]}...'")
        return self._retriever.retrieve_with_scores(query, k=k, company_id=company_id)

    @property
    def retriever(self) -> RetrieverPort:
        """Accès au port Retriever."""
        return self._retriever
