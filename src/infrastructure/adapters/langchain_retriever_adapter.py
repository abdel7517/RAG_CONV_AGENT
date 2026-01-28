"""
Adapter LangChain Retriever - Implémentation du RetrieverPort.

Cet adapter wrap l'implémentation existante Retriever et l'expose
via l'interface RetrieverPort.
"""

import logging
from typing import List, Optional, Tuple, Any

from src.domain.ports.retriever_port import RetrieverPort
from src.domain.ports.vector_store_port import VectorStorePort
from src.retrieval.retriever import Retriever

logger = logging.getLogger(__name__)


class LangChainRetrieverAdapter(RetrieverPort):
    """
    Adapter qui implémente RetrieverPort en utilisant le Retriever LangChain.

    Usage:
        vector_store = PGVectorAdapter()
        retriever = LangChainRetrieverAdapter(vector_store)
        docs = retriever.retrieve("query", company_id="techstore")

    Tests:
        mock_retriever = Mock(spec=RetrieverPort)
    """

    def __init__(self, vector_store: VectorStorePort):
        """
        Initialise l'adapter avec un VectorStorePort.

        Args:
            vector_store: Port du vector store (pas l'implémentation concrète)
        """
        # Le Retriever existant attend un VectorStore concret
        # On accède à l'implémentation via la propriété
        if hasattr(vector_store, 'implementation'):
            self._impl = Retriever(vector_store.implementation)
        else:
            # Fallback pour les mocks ou autres implémentations
            self._impl = Retriever(vector_store)
        logger.debug("LangChainRetrieverAdapter initialisé")

    def retrieve(
        self,
        query: str,
        k: Optional[int] = None,
        company_id: Optional[str] = None
    ) -> List[Any]:
        """
        Récupère les documents pertinents.

        Args:
            query: Requête de recherche
            k: Nombre de documents
            company_id: Filtre multi-tenant

        Returns:
            Liste de Documents LangChain
        """
        logger.debug(f"LangChainRetrieverAdapter.retrieve: query='{query[:50]}...', company_id={company_id}")
        return self._impl.retrieve(query, k=k, company_id=company_id)

    def retrieve_formatted(
        self,
        query: str,
        k: Optional[int] = None,
        company_id: Optional[str] = None
    ) -> str:
        """
        Récupère et formate les documents.

        Args:
            query: Requête de recherche
            k: Nombre de documents
            company_id: Filtre multi-tenant

        Returns:
            Documents formatés en texte
        """
        logger.debug(f"LangChainRetrieverAdapter.retrieve_formatted: query='{query[:50]}...'")
        return self._impl.retrieve_formatted(query, k=k, company_id=company_id)

    def retrieve_with_scores(
        self,
        query: str,
        k: Optional[int] = None,
        company_id: Optional[str] = None
    ) -> List[Tuple[Any, float]]:
        """
        Récupère les documents avec leurs scores.

        Args:
            query: Requête de recherche
            k: Nombre de documents
            company_id: Filtre multi-tenant

        Returns:
            Liste de tuples (Document, score)
        """
        logger.debug(f"LangChainRetrieverAdapter.retrieve_with_scores: query='{query[:50]}...'")
        return self._impl.retrieve_with_scores(query, k=k, company_id=company_id)
