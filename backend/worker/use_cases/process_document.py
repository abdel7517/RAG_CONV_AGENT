"""Use case: Vectorisation d'un document PDF dans le worker."""

import json
import logging
import os
import tempfile

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.domain.models.document import DocumentStatus
from backend.domain.ports.document_repository_port import DocumentRepositoryPort
from backend.domain.ports.event_broker_port import EventBrokerPort
from backend.domain.ports.file_storage_port import FileStoragePort
from src.config import settings
from src.domain.ports.vector_store_port import VectorStorePort

logger = logging.getLogger(__name__)

BATCH_SIZE = 10


class ProcessDocumentUseCase:
    """
    Pipeline de vectorisation d'un document PDF:
    1. Telecharge le fichier depuis GCS
    2. Chunk le PDF (PyPDFLoader + RecursiveCharacterTextSplitter)
    3. Stocke les embeddings dans pgvector (par batch avec progression)
    4. Notifie la progression via SSE (Redis pub/sub)
    """

    def __init__(
        self,
        repo: DocumentRepositoryPort,
        storage: FileStoragePort,
        event_broker: EventBrokerPort,
        vector_store: VectorStorePort,
    ):
        self._repo = repo
        self._storage = storage
        self._broker = event_broker
        self._vector_store = vector_store

    async def execute(self, job_payload: dict) -> None:
        document_id = job_payload["document_id"]
        company_id = job_payload["company_id"]
        gcs_path = job_payload["gcs_path"]
        channel = f"document_progress:{document_id}"

        try:
            file_content = await self._download(document_id, gcs_path, channel)
            chunks = await self._chunk(document_id, company_id, file_content, channel)
            await self._embed(document_id, chunks, channel)
            await self._complete(document_id, len(chunks), gcs_path, channel)
        except Exception as e:
            await self._fail(document_id, e, channel)

    # ── Pipeline steps ──────────────────────────────────────────────────

    async def _download(self, document_id: str, gcs_path: str, channel: str) -> bytes:
        """Telecharge le fichier depuis GCS (0% -> 10%)."""
        await self._publish_progress(
            channel, document_id, "downloading", 0,
            "Telechargement du fichier..."
        )
        file_content = await self._storage.download(gcs_path)
        await self._publish_progress(
            channel, document_id, "downloading", 10,
            "Fichier telecharge"
        )
        return file_content

    async def _chunk(
        self, document_id: str, company_id: str, file_content: bytes, channel: str,
    ) -> list:
        """Decoupe le PDF en chunks (10% -> 20%)."""
        await self._repo.update_status(document_id, DocumentStatus.VECTORIZING)
        await self._publish_progress(
            channel, document_id, "vectorizing", 10,
            "Decoupage du document en chunks..."
        )

        document = await self._repo.get_by_id(document_id, company_id)
        filename = document.filename if document else "unknown.pdf"
        chunks = self._chunk_pdf(file_content, filename, company_id, document_id)

        await self._publish_progress(
            channel, document_id, "vectorizing", 20,
            f"{len(chunks)} chunk(s) cree(s)"
        )
        return chunks

    async def _embed(self, document_id: str, chunks: list, channel: str) -> None:
        """Stocke les embeddings par batch dans pgvector (20% -> 95%)."""
        total_chunks = len(chunks)
        if total_chunks == 0:
            return

        batches = [chunks[i:i + BATCH_SIZE] for i in range(0, total_chunks, BATCH_SIZE)]
        total_batches = len(batches)

        for batch_idx, batch in enumerate(batches):
            await self._vector_store.add_documents(batch)

            progress = 20 + int(((batch_idx + 1) / total_batches) * 75)
            processed = min((batch_idx + 1) * BATCH_SIZE, total_chunks)
            await self._publish_progress(
                channel, document_id, "vectorizing", progress,
                f"Indexation: {processed}/{total_chunks} chunks"
            )

    async def _complete(self, document_id: str, total_chunks: int, gcs_path: str, channel: str) -> None:
        """Finalise le traitement et supprime le fichier source de GCS (100%)."""
        await self._repo.update_status(document_id, DocumentStatus.COMPLETED)
        await self._storage.delete(gcs_path)
        await self._publish_progress(
            channel, document_id, "completed", 100,
            "Traitement termine", done=True
        )
        logger.info(f"Document {document_id} vectorized successfully ({total_chunks} chunks), GCS file deleted")

    async def _fail(self, document_id: str, error: Exception, channel: str) -> None:
        """Marque le document en echec."""
        logger.error(f"Error processing document {document_id}: {error}")
        await self._repo.update_status(
            document_id, DocumentStatus.FAILED, error_message=str(error)
        )
        await self._publish_progress(
            channel, document_id, "failed", 0,
            str(error), done=True
        )

    # ── Helpers ──────────────────────────────────────────────────────────

    def _chunk_pdf(
        self,
        content: bytes,
        filename: str,
        company_id: str,
        document_id: str,
    ) -> list:
        """Charge un PDF depuis les bytes et le decoupe en chunks."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            loader = PyPDFLoader(tmp_path)
            documents = loader.load()

            splitter = RecursiveCharacterTextSplitter(
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP,
                length_function=len,
                separators=["\n\n", "\n", " ", ""],
            )
            chunks = splitter.split_documents(documents)

            for chunk in chunks:
                chunk.metadata["company_id"] = company_id
                chunk.metadata["document_id"] = document_id
                chunk.metadata["source"] = filename

            return chunks
        finally:
            os.unlink(tmp_path)

    async def _publish_progress(
        self,
        channel: str,
        document_id: str,
        step: str,
        progress: int,
        message: str,
        done: bool = False,
    ) -> None:
        """Publie un evenement de progression via Redis pub/sub."""
        event = json.dumps({
            "document_id": document_id,
            "step": step,
            "progress": progress,
            "message": message,
            "done": done,
        })
        await self._broker.publish(channel=channel, message=event)
