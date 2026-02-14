"""Port abstrait pour le repository des entreprises."""

from abc import ABC, abstractmethod
from typing import Optional

from backend.domain.models.company import Company


class CompanyRepositoryPort(ABC):
    """
    Interface pour l'acces aux entreprises en base.

    Implementations possibles:
    - PostgresCompanyRepository (psycopg3 async)
    - InMemoryCompanyRepository (pour tests)
    """

    @abstractmethod
    async def get_by_api_key(self, api_key: str) -> Optional[Company]:
        """Recupere une entreprise par son API key."""
        ...

    @abstractmethod
    async def get_by_id(self, company_id: str) -> Optional[Company]:
        """Recupere une entreprise par son ID."""
        ...
