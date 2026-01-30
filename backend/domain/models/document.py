"""Modele domain et schemas API pour la gestion des documents PDF."""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Optional

from pydantic import BaseModel

from backend.domain.exceptions import (
    DocumentNotFoundError,
    InvalidFileTypeError,
    FileTooLargeError,
)


@dataclass
class Document:
    """
    Metadonnees d'un document PDF uploade.

    Utiliser Document.create() pour creer un nouveau document avec validation.
    Le constructeur direct est reserve a la reconstitution depuis la persistence.
    """

    document_id: str
    company_id: str
    filename: str
    size_bytes: int
    num_pages: int = 0
    content_type: str = "application/pdf"
    gcs_path: Optional[str] = None
    is_vectorized: bool = False
    uploaded_at: Optional[datetime] = None

    ALLOWED_CONTENT_TYPES: ClassVar[set[str]] = {"application/pdf"}

    @classmethod
    def create(
        cls,
        company_id: str,
        filename: str,
        size_bytes: int,
        content_type: str,
        max_upload_size_bytes: int,
        num_pages: int = 0,
    ) -> "Document":
        """
        Factory method: valide les inputs et cree un nouveau Document.

        Raises:
            InvalidFileTypeError: si le content_type n'est pas autorise.
            FileTooLargeError: si size_bytes depasse max_upload_size_bytes.
        """
        if content_type not in cls.ALLOWED_CONTENT_TYPES:
            raise InvalidFileTypeError(content_type)
        if size_bytes > max_upload_size_bytes:
            raise FileTooLargeError(size_bytes, max_upload_size_bytes)

        return cls(
            document_id=str(uuid.uuid4()),
            company_id=company_id,
            filename=filename,
            size_bytes=size_bytes,
            num_pages=num_pages,
            content_type=content_type,
        )

    @staticmethod
    def get_or_fail(document: Optional["Document"], document_id: str) -> "Document":
        """Verifie qu'un document existe. Leve DocumentNotFoundError sinon."""
        if document is None:
            raise DocumentNotFoundError(document_id)
        return document

    def assign_storage_path(self, gcs_path: str) -> None:
        """Assigne le chemin storage apres upload. Ne peut etre appele qu'une fois."""
        if self.gcs_path is not None:
            raise ValueError("Storage path already assigned")
        self.gcs_path = gcs_path


# --- Schemas API (Pydantic) ---


class DocumentResponse(BaseModel):
    """Schema de reponse pour un document."""

    document_id: str
    company_id: str
    filename: str
    size_bytes: int
    num_pages: int
    content_type: str
    is_vectorized: bool
    uploaded_at: str


class DocumentListResponse(BaseModel):
    """Schema de reponse pour la liste des documents."""

    documents: list[DocumentResponse]
    total: int


class DocumentUploadResponse(BaseModel):
    """Schema de reponse apres upload."""

    status: str
    document_id: str
    filename: str


class DocumentDeleteResponse(BaseModel):
    """Schema de reponse apres suppression."""

    status: str
    document_id: str
