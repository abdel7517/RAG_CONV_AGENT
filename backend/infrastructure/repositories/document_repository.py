"""Repository pour les metadonnees de documents dans PostgreSQL."""

import logging
from typing import Optional

import psycopg

from src.config import settings
from backend.domain.models.document import Document
from backend.domain.ports.document_repository_port import DocumentRepositoryPort

logger = logging.getLogger(__name__)


class PostgresDocumentRepository(DocumentRepositoryPort):
    """
    Acces aux metadonnees de documents dans PostgreSQL.
    Utilise psycopg3 async, meme pattern que CompanyRepository.
    """

    async def create(self, document: Document) -> None:
        async with await psycopg.AsyncConnection.connect(
            settings.get_postgres_uri()
        ) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO documents (
                        document_id, company_id, filename,
                        gcs_path, size_bytes, num_pages,
                        content_type, is_vectorized
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        document.document_id,
                        document.company_id,
                        document.filename,
                        document.gcs_path,
                        document.size_bytes,
                        document.num_pages,
                        document.content_type,
                        document.is_vectorized,
                    ),
                )
            await conn.commit()

        logger.info(
            f"Document '{document.filename}' ({document.document_id}) "
            f"saved for company {document.company_id}"
        )

    async def get_by_id(
        self, document_id: str, company_id: str
    ) -> Optional[Document]:
        async with await psycopg.AsyncConnection.connect(
            settings.get_postgres_uri()
        ) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT document_id, company_id, filename,
                           gcs_path, size_bytes, num_pages,
                           content_type, is_vectorized, uploaded_at
                    FROM documents
                    WHERE document_id = %s AND company_id = %s
                    """,
                    (document_id, company_id),
                )
                row = await cur.fetchone()

                if row:
                    return Document(
                        document_id=row[0],
                        company_id=row[1],
                        filename=row[2],
                        gcs_path=row[3],
                        size_bytes=row[4],
                        num_pages=row[5],
                        content_type=row[6],
                        is_vectorized=row[7],
                        uploaded_at=row[8],
                    )
                return None

    async def list_by_company(self, company_id: str) -> list[Document]:
        async with await psycopg.AsyncConnection.connect(
            settings.get_postgres_uri()
        ) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT document_id, company_id, filename,
                           gcs_path, size_bytes, num_pages,
                           content_type, is_vectorized, uploaded_at
                    FROM documents
                    WHERE company_id = %s
                    ORDER BY uploaded_at DESC
                    """,
                    (company_id,),
                )
                rows = await cur.fetchall()

                return [
                    Document(
                        document_id=r[0],
                        company_id=r[1],
                        filename=r[2],
                        gcs_path=r[3],
                        size_bytes=r[4],
                        num_pages=r[5],
                        content_type=r[6],
                        is_vectorized=r[7],
                        uploaded_at=r[8],
                    )
                    for r in rows
                ]

    async def get_total_pages(self, company_id: str) -> int:
        async with await psycopg.AsyncConnection.connect(
            settings.get_postgres_uri()
        ) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT COALESCE(SUM(num_pages), 0) FROM documents WHERE company_id = %s",
                    (company_id,),
                )
                row = await cur.fetchone()
                return row[0] if row else 0

    async def delete(self, document_id: str, company_id: str) -> bool:
        async with await psycopg.AsyncConnection.connect(
            settings.get_postgres_uri()
        ) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM documents WHERE document_id = %s AND company_id = %s",
                    (document_id, company_id),
                )
                deleted = cur.rowcount > 0
            await conn.commit()

        if deleted:
            logger.info(f"Document {document_id} deleted for {company_id}")
        return deleted
