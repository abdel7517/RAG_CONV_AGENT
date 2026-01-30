"""Use case: Upload d'un document PDF."""

import logging

from backend.domain.exceptions import PageLimitExceededError
from backend.domain.models.document import Document
from backend.domain.ports.document_repository_port import DocumentRepositoryPort
from backend.domain.ports.file_storage_port import FileStoragePort
from backend.domain.ports.pdf_analyzer_port import PdfAnalyzerPort
from src.config import settings

logger = logging.getLogger(__name__)


class UploadDocumentUseCase:
    """
    Upload un document PDF vers le storage et sauvegarde ses metadonnees.

    La validation (content_type, taille) est deleguee a Document.create().
    Le comptage de pages et la verification du quota sont geres ici.
    """

    def __init__(
        self,
        storage: FileStoragePort,
        repo: DocumentRepositoryPort,
        pdf_analyzer: PdfAnalyzerPort,
    ):
        self._storage = storage
        self._repo = repo
        self._pdf_analyzer = pdf_analyzer

    async def execute(
        self,
        company_id: str,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> Document:
        # 1. Compter les pages du PDF
        num_pages = self._pdf_analyzer.count_pages(content)

        # 2. Verifier la limite de pages
        current_total = await self._repo.get_total_pages(company_id)
        max_pages = settings.MAX_PAGES_PER_COMPANY
        if current_total + num_pages > max_pages:
            raise PageLimitExceededError(current_total, num_pages, max_pages)

        # 3. Creer le Document (validation type + taille)
        document = Document.create(
            company_id=company_id,
            filename=filename,
            size_bytes=len(content),
            content_type=content_type,
            max_upload_size_bytes=settings.MAX_UPLOAD_SIZE_BYTES,
            num_pages=num_pages,
        )

        # 4. Upload vers le storage
        gcs_path = await self._storage.upload(
            company_id=document.company_id,
            document_id=document.document_id,
            file_content=content,
            content_type=document.content_type,
        )

        # 5. Persister les metadonnees
        document.assign_storage_path(gcs_path)
        await self._repo.create(document)

        return document
