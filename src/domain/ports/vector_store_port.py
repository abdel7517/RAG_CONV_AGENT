"""
Port (Interface) pour le stockage vectoriel.

Ce port définit le contrat que tout adapter de stockage vectoriel
doit implémenter (PGVector, Pinecone, Chroma, etc.).
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Any


class VectorStorePort(ABC):
    """
    Interface pour le stockage et la recherche vectorielle.

    Implémentations possibles:
    - PGVectorAdapter (PostgreSQL + pgvector)
    - PineconeAdapter
    - ChromaAdapter
    - MockVectorStore (pour les tests)
    """

    @abstractmethod
    def similarity_search(
        self,
        query: str,
        k: Optional[int] = None,
        company_id: Optional[str] = None
    ) -> List[Any]:
        """
        Recherche les documents les plus similaires à la requête.

        Args:
            query: Texte de recherche
            k: Nombre de résultats à retourner
            company_id: Filtre multi-tenant

        Returns:
            Liste de documents (format dépend de l'implémentation)
        """
        pass

    @abstractmethod
    def similarity_search_with_score(
        self,
        query: str,
        k: Optional[int] = None,
        company_id: Optional[str] = None
    ) -> List[Tuple[Any, float]]:
        """
        Recherche avec scores de similarité.

        Args:
            query: Texte de recherche
            k: Nombre de résultats
            company_id: Filtre multi-tenant

        Returns:
            Liste de tuples (document, score)
        """
        pass
