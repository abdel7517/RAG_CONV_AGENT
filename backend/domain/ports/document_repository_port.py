"""Port abstrait pour le repository de metadonnees de documents."""

from abc import ABC, abstractmethod
from typing import Optional

from backend.domain.models.document import Document


class DocumentRepositoryPort(ABC):
    """
    Interface pour l'acces aux metadonnees de documents en base.

    Implementations possibles:
    - PostgresDocumentRepository (psycopg3 async)
    - InMemoryDocumentRepository (pour tests)
    """

    @abstractmethod
    async def create(self, document: Document) -> None:
        """Sauvegarde les metadonnees d'un document."""
        ...

    @abstractmethod
    async def get_by_id(
        self, document_id: str, company_id: str
    ) -> Optional[Document]:
        """Recupere un document par son ID (scope company_id)."""
        ...

    @abstractmethod
    async def list_by_company(self, company_id: str) -> list[Document]:
        """Liste tous les documents d'une entreprise."""
        ...

    @abstractmethod
    async def delete(self, document_id: str, company_id: str) -> bool:
        """Supprime les metadonnees d'un document. Returns True si supprime."""
        ...

    @abstractmethod
    async def get_total_pages(self, company_id: str) -> int:
        """Retourne le nombre total de pages PDF pour une entreprise."""
        ...
