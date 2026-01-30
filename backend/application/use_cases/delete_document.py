"""Use case: Suppression d'un document."""

from backend.domain.models.document import Document
from backend.domain.ports.document_repository_port import DocumentRepositoryPort
from backend.domain.ports.file_storage_port import FileStoragePort


class DeleteDocumentUseCase:
    """
    Supprime un document du storage et de la base de donnees.

    La validation d'existence est deleguee a Document.get_or_fail().
    """

    def __init__(self, storage: FileStoragePort, repo: DocumentRepositoryPort):
        self._storage = storage
        self._repo = repo

    async def execute(self, document_id: str, company_id: str) -> None:
        document = Document.get_or_fail(
            await self._repo.get_by_id(document_id, company_id),
            document_id,
        )

        await self._storage.delete(document.gcs_path)
        await self._repo.delete(document_id, company_id)
