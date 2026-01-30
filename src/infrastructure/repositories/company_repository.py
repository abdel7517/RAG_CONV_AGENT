"""
Repository pour l'acces aux donnees entreprise dans PostgreSQL.
"""

import logging
from typing import Optional

import psycopg

from src.config import settings
from src.domain.models.company import Company, CompanyPlan

logger = logging.getLogger(__name__)


class CompanyRepository:
    """
    Acces aux donnees entreprise dans PostgreSQL.

    Utilise psycopg3 pour les operations synchrones et asynchrones.
    """

    async def get_by_id(self, company_id: str) -> Optional[Company]:
        """
        Recupere une entreprise par son ID.

        Args:
            company_id: Identifiant unique de l'entreprise

        Returns:
            Company si trouvee, None sinon
        """
        async with await psycopg.AsyncConnection.connect(
            settings.get_postgres_uri()
        ) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT company_id, name, tone, plan FROM companies WHERE company_id = %s",
                    (company_id,)
                )
                row = await cur.fetchone()

                if row:
                    return Company(
                        company_id=row[0],
                        name=row[1],
                        tone=row[2],
                        plan=CompanyPlan(row[3]) if row[3] else CompanyPlan.FREE,
                    )
                return None

    async def create(self, company: Company) -> None:
        """
        Cree ou met a jour une entreprise.

        Args:
            company: Instance Company a sauvegarder
        """
        async with await psycopg.AsyncConnection.connect(
            settings.get_postgres_uri()
        ) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO companies (company_id, name, tone, plan)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (company_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        tone = EXCLUDED.tone,
                        plan = EXCLUDED.plan
                    """,
                    (company.company_id, company.name, company.tone, company.plan.value)
                )
            await conn.commit()

        logger.info(f"Entreprise '{company.name}' ({company.company_id}) sauvegardee")

    async def list_all(self) -> list[Company]:
        """
        Liste toutes les entreprises.

        Returns:
            Liste de Company
        """
        async with await psycopg.AsyncConnection.connect(
            settings.get_postgres_uri()
        ) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT company_id, name, tone, plan FROM companies ORDER BY name"
                )
                rows = await cur.fetchall()

                return [
                    Company(
                        company_id=row[0],
                        name=row[1],
                        tone=row[2],
                        plan=CompanyPlan(row[3]) if row[3] else CompanyPlan.FREE,
                    )
                    for row in rows
                ]

    async def delete(self, company_id: str) -> bool:
        """
        Supprime une entreprise.

        Args:
            company_id: ID de l'entreprise a supprimer

        Returns:
            True si supprimee, False si non trouvee
        """
        async with await psycopg.AsyncConnection.connect(
            settings.get_postgres_uri()
        ) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM companies WHERE company_id = %s",
                    (company_id,)
                )
                deleted = cur.rowcount > 0
            await conn.commit()

        if deleted:
            logger.info(f"Entreprise {company_id} supprimee")
        return deleted
