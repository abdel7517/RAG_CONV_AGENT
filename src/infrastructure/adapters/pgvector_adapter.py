"""
Adapter PGVector - Implémentation du VectorStorePort avec PostgreSQL/pgvector.

Cet adapter wrap l'implémentation existante VectorStore et l'expose
via l'interface VectorStorePort.
"""

import logging
from typing import List, Optional, Tuple, Any

from src.domain.ports.vector_store_port import VectorStorePort
from src.retrieval.vector_store import VectorStore

logger = logging.getLogger(__name__)


class PGVectorAdapter(VectorStorePort):
    """
    Adapter qui implémente VectorStorePort en utilisant PGVector.

    Wrap l'implémentation existante src.retrieval.vector_store.VectorStore
    pour respecter le contrat défini par le port.

    Usage:
        adapter = PGVectorAdapter()
        docs = adapter.similarity_search("query", company_id="techstore")

    Tests:
        # L'adapter peut être remplacé par un mock du port
        mock_store = Mock(spec=VectorStorePort)
    """

    def __init__(self, vector_store: VectorStore = None):
        """
        Initialise l'adapter avec une implémentation VectorStore.

        Args:
            vector_store: Instance existante ou None pour créer une nouvelle
        """
        self._impl = vector_store or VectorStore()
        logger.debug("PGVectorAdapter initialisé")

    def similarity_search(
        self,
        query: str,
        k: Optional[int] = None,
        company_id: Optional[str] = None
    ) -> List[Any]:
        """
        Recherche de similarité via PGVector.

        Args:
            query: Texte de recherche
            k: Nombre de résultats
            company_id: Filtre multi-tenant

        Returns:
            Liste de Documents LangChain
        """
        logger.debug(f"PGVectorAdapter.similarity_search: query='{query[:50]}...', company_id={company_id}")
        return self._impl.similarity_search(query, k=k, company_id=company_id)

    def similarity_search_with_score(
        self,
        query: str,
        k: Optional[int] = None,
        company_id: Optional[str] = None
    ) -> List[Tuple[Any, float]]:
        """
        Recherche avec scores via PGVector.

        Args:
            query: Texte de recherche
            k: Nombre de résultats
            company_id: Filtre multi-tenant

        Returns:
            Liste de tuples (Document, score)
        """
        logger.debug(f"PGVectorAdapter.similarity_search_with_score: query='{query[:50]}...'")
        return self._impl.similarity_search_with_score(query, k=k, company_id=company_id)

    @property
    def implementation(self) -> VectorStore:
        """Accès à l'implémentation sous-jacente (pour cas spéciaux)."""
        return self._impl
