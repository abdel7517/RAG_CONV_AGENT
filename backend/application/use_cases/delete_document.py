"""Use case: Suppression d'un document."""

from backend.domain.models.document import Document
from backend.domain.ports.document_repository_port import DocumentRepositoryPort
from backend.domain.ports.file_storage_port import FileStoragePort
from src.domain.ports.vector_store_port import VectorStorePort


class DeleteDocumentUseCase:
    """
    Supprime un document du storage, de la base de donnees et du vector store.

    La validation d'existence est deleguee a Document.get_or_fail().
    """

    def __init__(
        self,
        storage: FileStoragePort,
        repo: DocumentRepositoryPort,
        vector_store: VectorStorePort,
    ):
        self._storage = storage
        self._repo = repo
        self._vector_store = vector_store

    async def execute(self, document_id: str, company_id: str) -> None:
        document = Document.get_or_fail(
            await self._repo.get_by_id(document_id, company_id),
            document_id,
        )

        # Supprimer les vecteurs du vector store
        await self._vector_store.delete_by_document_id(document_id)

        # Supprimer le fichier de GCS
        if document.gcs_path:
            await self._storage.delete(document.gcs_path)

        # Supprimer les métadonnées de la DB
        await self._repo.delete(document_id, company_id)
