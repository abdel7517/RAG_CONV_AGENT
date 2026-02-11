"""Use case: Upload d'un document PDF (validation, GCS, enqueue vectorisation)."""

import logging

from backend.domain.exceptions import PageLimitExceededError
from backend.domain.models.document import Document
from backend.domain.ports.document_repository_port import DocumentRepositoryPort
from backend.domain.ports.file_storage_port import FileStoragePort
from backend.domain.ports.job_queue_port import JobQueuePort
from backend.domain.ports.pdf_analyzer_port import PdfAnalyzerPort
from src.config import settings

logger = logging.getLogger(__name__)


class UploadDocumentUseCase:
    """
    Recoit un fichier PDF, valide, compte les pages, verifie le quota,
    upload vers GCS, persiste les metadonnees, et enqueue la vectorisation.

    Le worker ne recoit que {document_id, company_id, gcs_path} via Redis.
    """

    def __init__(
        self,
        repo: DocumentRepositoryPort,
        job_queue: JobQueuePort,
        storage: FileStoragePort,
        pdf_analyzer: PdfAnalyzerPort,
    ):
        self._repo = repo
        self._job_queue = job_queue
        self._storage = storage
        self._pdf_analyzer = pdf_analyzer

    async def execute(
        self,
        company_id: str,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> Document:
        # 1. Creer le Document (validation type + taille)
        document = Document.create(
            company_id=company_id,
            filename=filename,
            size_bytes=len(content),
            content_type=content_type,
            max_upload_size_bytes=settings.MAX_UPLOAD_SIZE_BYTES,
        )

        # 2. Compter les pages du PDF
        num_pages = self._pdf_analyzer.count_pages(content)
        document.num_pages = num_pages

        # 3. Verifier le quota de pages
        current_total = await self._repo.get_total_pages(company_id)
        max_pages = settings.MAX_PAGES_PER_COMPANY
        if current_total + num_pages > max_pages:
            raise PageLimitExceededError(current_total, num_pages, max_pages)

        # 4. Upload vers GCS
        gcs_path = await self._storage.upload(
            company_id=company_id,
            document_id=document.document_id,
            file_content=content,
            content_type=content_type,
        )
        document.gcs_path = gcs_path

        # 5. Persister les metadonnees completes (status=queued, gcs_path + num_pages set)
        await self._repo.create(document)

        # 6. Enqueue le job pour le worker via ARQ
        await self._job_queue.enqueue(
            "process_document",
            document_id=document.document_id,
            company_id=company_id,
            gcs_path=gcs_path,
        )

        logger.info(
            f"Document {document.document_id} uploaded and queued for vectorization "
            f"(company={company_id}, file={filename}, pages={num_pages})"
        )
        return document
