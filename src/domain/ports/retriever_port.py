"""
Port (Interface) pour la récupération de documents.

Ce port définit le contrat pour les retrievers qui orchestrent
la recherche et le formatage des documents.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Any


class RetrieverPort(ABC):
    """
    Interface pour la récupération de documents.

    Le retriever utilise un VectorStore pour la recherche
    et ajoute la logique de formatage et d'orchestration.

    Implémentations possibles:
    - PGVectorAdapter (implémente aussi VectorStorePort)
    - MockRetriever (pour les tests)
    """

    @abstractmethod
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
            Liste de documents
        """
        pass

    @abstractmethod
    def retrieve_formatted(
        self,
        query: str,
        k: Optional[int] = None,
        company_id: Optional[str] = None
    ) -> str:
        """
        Récupère et formate les documents en chaîne.

        Args:
            query: Requête de recherche
            k: Nombre de documents
            company_id: Filtre multi-tenant

        Returns:
            Documents formatés en texte
        """
        pass

    @abstractmethod
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
            Liste de tuples (document, score)
        """
        pass
