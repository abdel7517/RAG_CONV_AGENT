"""Port abstrait pour l'analyse de fichiers PDF."""

from abc import ABC, abstractmethod


class PdfAnalyzerPort(ABC):
    """
    Interface abstraite pour l'analyse de fichiers PDF.

    Implementations possibles:
    - PypdfAnalyzerAdapter (pypdf)
    """

    @abstractmethod
    def count_pages(self, content: bytes) -> int:
        """
        Compte le nombre de pages d'un PDF.

        Args:
            content: Contenu binaire du fichier PDF

        Returns:
            Nombre de pages
        """
        ...
