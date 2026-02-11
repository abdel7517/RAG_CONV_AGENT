"""Adapter ARQ pour la file d'attente de jobs."""

import logging
from typing import Optional
from urllib.parse import urlparse

from arq.connections import ArqRedis, RedisSettings, create_pool

from backend.domain.ports.job_queue_port import JobQueuePort

logger = logging.getLogger(__name__)


def parse_redis_settings(url: str) -> RedisSettings:
    """Parse une URL Redis en RedisSettings ARQ."""
    parsed = urlparse(url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        password=parsed.password,
        database=int(parsed.path.lstrip("/") or "0"),
    )


class ArqJobQueueAdapter(JobQueuePort):
    """
    Implementation du JobQueuePort utilisant ARQ (async Redis queue).

    Le pool Redis est cree paresseusement au premier appel enqueue().
    ARQ gere la serialisation, le retry et le suivi des jobs.
    """

    def __init__(self, redis_settings: RedisSettings):
        self._settings = redis_settings
        self._pool: Optional[ArqRedis] = None

    async def _get_pool(self) -> ArqRedis:
        if self._pool is None:
            self._pool = await create_pool(self._settings)
        return self._pool

    async def enqueue(self, job_name: str, **kwargs) -> None:
        pool = await self._get_pool()
        job = await pool.enqueue_job(job_name, **kwargs)
        logger.info(f"Job enqueued: {job_name} (job_id={job.job_id})")

    async def close(self) -> None:
        if self._pool:
            await self._pool.aclose()
            self._pool = None
