"""Port abstrait pour le stockage de fichiers (GCS, S3, local, etc.)."""

from abc import ABC, abstractmethod


class FileStoragePort(ABC):
    """
    Interface abstraite pour le stockage de fichiers.

    Implementations possibles:
    - GCSFileStorageAdapter (Google Cloud Storage)
    - LocalFileStorageAdapter (filesystem local, pour dev/tests)
    """

    @abstractmethod
    async def upload(
        self,
        company_id: str,
        document_id: str,
        file_content: bytes,
        content_type: str = "application/pdf",
    ) -> str:
        """
        Upload un fichier vers le storage.

        Args:
            company_id: ID entreprise (prefix du path)
            document_id: ID unique du document
            file_content: Contenu binaire du fichier
            content_type: Type MIME

        Returns:
            Chemin dans le storage (ex: "company_id/document_id.pdf")
        """
        ...

    @abstractmethod
    async def delete(self, gcs_path: str) -> bool:
        """
        Supprime un fichier du storage.

        Args:
            gcs_path: Chemin du fichier dans le storage

        Returns:
            True si supprime, False sinon
        """
        ...

