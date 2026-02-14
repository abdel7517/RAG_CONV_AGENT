"""Repository pour les entreprises dans PostgreSQL."""

import logging
from typing import Optional

import psycopg

from src.config import settings
from backend.domain.models.company import Company
from backend.domain.ports.company_repository_port import CompanyRepositoryPort

logger = logging.getLogger(__name__)


class PostgresCompanyRepository(CompanyRepositoryPort):
    """
    Acces aux entreprises dans PostgreSQL.
    Utilise psycopg3 async, meme pattern que UserRepository.
    """

    async def get_by_api_key(self, api_key: str) -> Optional[Company]:
        async with await psycopg.AsyncConnection.connect(
            settings.get_postgres_uri()
        ) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT company_id, name, api_key, tone, plan, created_at
                    FROM companies
                    WHERE api_key = %s
                    """,
                    (api_key,),
                )
                row = await cur.fetchone()
                if row:
                    return Company(
                        company_id=row[0],
                        name=row[1],
                        api_key=row[2],
                        tone=row[3],
                        plan=row[4],
                        created_at=row[5],
                    )
                return None

    async def get_by_id(self, company_id: str) -> Optional[Company]:
        async with await psycopg.AsyncConnection.connect(
            settings.get_postgres_uri()
        ) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT company_id, name, api_key, tone, plan, created_at
                    FROM companies
                    WHERE company_id = %s
                    """,
                    (company_id,),
                )
                row = await cur.fetchone()

                if row:
                    return Company(
                        company_id=row[0],
                        name=row[1],
                        api_key=row[2],
                        tone=row[3],
                        plan=row[4],
                        created_at=row[5],
                    )
                return None
