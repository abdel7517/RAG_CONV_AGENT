"""Port abstrait pour le repository des utilisateurs."""

from abc import ABC, abstractmethod
from typing import Optional

from backend.domain.models.user import User


class UserRepositoryPort(ABC):
    """
    Interface pour l'acces aux utilisateurs en base.

    Implementations possibles:
    - PostgresUserRepository (psycopg3 async)
    - InMemoryUserRepository (pour tests)
    """

    @abstractmethod
    async def create(self, user: User) -> None:
        """Sauvegarde un nouvel utilisateur."""
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Recupere un utilisateur par son email."""
        ...

    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Recupere un utilisateur par son ID."""
        ...

    @abstractmethod
    async def email_exists(self, email: str) -> bool:
        """Verifie si un email est deja utilise."""
        ...
