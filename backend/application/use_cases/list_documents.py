"""Use case: Liste des documents d'une entreprise."""

from backend.domain.models.document import Document
from backend.domain.ports.document_repository_port import DocumentRepositoryPort


class ListDocumentsUseCase:
    """Liste tous les documents d'une entreprise."""

    def __init__(self, repo: DocumentRepositoryPort):
        self._repo = repo

    async def execute(self, company_id: str) -> list[Document]:
        return await self._repo.list_by_company(company_id)
