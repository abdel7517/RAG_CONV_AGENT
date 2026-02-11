"""Port abstrait pour la file d'attente de jobs."""

from abc import ABC, abstractmethod


class JobQueuePort(ABC):
    """
    Interface abstraite pour une file d'attente de jobs.

    Implementations possibles:
    - ArqJobQueueAdapter (ARQ + Redis)
    - InMemoryJobQueueAdapter (pour tests)
    """

    @abstractmethod
    async def enqueue(self, job_name: str, **kwargs) -> None:
        """
        Enqueue un job par son nom avec des arguments.

        Args:
            job_name: Nom de la fonction a executer cote worker
            **kwargs: Arguments passes a la fonction
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Ferme la connexion."""
        ...
