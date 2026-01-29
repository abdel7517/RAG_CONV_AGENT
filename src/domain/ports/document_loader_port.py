"""
Port (Interface) pour le chargement de documents.

Ce port definit le contrat pour les loaders qui chargent
et decoupent les documents en chunks pour le RAG.
"""

from abc import ABC, abstractmethod
from typing import List, Any


class DocumentLoaderPort(ABC):
    """
    Interface pour le chargement et le decoupage de documents.

    Implementations possibles:
    - PDFDocumentLoaderAdapter (PDF via PyPDF)
    - MockDocumentLoader (pour les tests)
    """

    @abstractmethod
    def load_and_split(
        self,
        company_id: str = None
    ) -> List[Any]:
        """
        Charge les documents et les decoupe en chunks.

        Args:
            company_id: Si fourni, ajoute company_id aux metadata
                       pour le filtrage multi-tenant.

        Returns:
            Liste de chunks (Documents) avec metadata enrichies
        """
        pass
