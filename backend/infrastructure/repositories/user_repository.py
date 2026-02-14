"""Repository pour les utilisateurs dans PostgreSQL."""

import logging
from typing import Optional

import psycopg

from src.config import settings
from backend.domain.models.user import User
from backend.domain.ports.user_repository_port import UserRepositoryPort

logger = logging.getLogger(__name__)


class PostgresUserRepository(UserRepositoryPort):
    """
    Acces aux utilisateurs dans PostgreSQL.
    Utilise psycopg3 async, meme pattern que DocumentRepository.
    """

    async def create(self, user: User) -> None:
        async with await psycopg.AsyncConnection.connect(
            settings.get_postgres_uri()
        ) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO users (
                        user_id, email, hashed_password,
                        company_id, full_name, disabled
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user.user_id,
                        user.email,
                        user.hashed_password,
                        user.company_id,
                        user.full_name,
                        user.disabled,
                    ),
                )
            await conn.commit()

        logger.info(f"User '{user.email}' ({user.user_id}) created for company {user.company_id}")

    async def get_by_email(self, email: str) -> Optional[User]:
        async with await psycopg.AsyncConnection.connect(
            settings.get_postgres_uri()
        ) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT user_id, email, hashed_password,
                           company_id, full_name, disabled, created_at
                    FROM users
                    WHERE email = %s
                    """,
                    (email,),
                )
                row = await cur.fetchone()

                if row:
                    return User(
                        user_id=row[0],
                        email=row[1],
                        hashed_password=row[2],
                        company_id=row[3],
                        full_name=row[4],
                        disabled=row[5],
                        created_at=row[6],
                    )
                return None

    async def get_by_id(self, user_id: str) -> Optional[User]:
        async with await psycopg.AsyncConnection.connect(
            settings.get_postgres_uri()
        ) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT user_id, email, hashed_password,
                           company_id, full_name, disabled, created_at
                    FROM users
                    WHERE user_id = %s
                    """,
                    (user_id,),
                )
                row = await cur.fetchone()

                if row:
                    return User(
                        user_id=row[0],
                        email=row[1],
                        hashed_password=row[2],
                        company_id=row[3],
                        full_name=row[4],
                        disabled=row[5],
                        created_at=row[6],
                    )
                return None

    async def email_exists(self, email: str) -> bool:
        async with await psycopg.AsyncConnection.connect(
            settings.get_postgres_uri()
        ) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT 1 FROM users WHERE email = %s LIMIT 1",
                    (email,),
                )
                row = await cur.fetchone()
                return row is not None
