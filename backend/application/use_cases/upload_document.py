"""Use case: Upload d'un document PDF."""

from backend.domain.models.document import Document
from backend.domain.ports.document_repository_port import DocumentRepositoryPort
from backend.domain.ports.file_storage_port import FileStoragePort
from src.config import settings


class UploadDocumentUseCase:
    """
    Upload un document PDF vers le storage et sauvegarde ses metadonnees.

    La validation (content_type, taille) est deleguee a Document.create().
    """

    def __init__(self, storage: FileStoragePort, repo: DocumentRepositoryPort):
        self._storage = storage
        self._repo = repo

    async def execute(
        self,
        company_id: str,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> Document:
        document = Document.create(
            company_id=company_id,
            filename=filename,
            size_bytes=len(content),
            content_type=content_type,
            max_upload_size_bytes=settings.MAX_UPLOAD_SIZE_BYTES,
        )

        gcs_path = await self._storage.upload(
            company_id=document.company_id,
            document_id=document.document_id,
            file_content=content,
            content_type=document.content_type,
        )

        document.assign_storage_path(gcs_path)
        await self._repo.create(document)

        return document
