"""Configuration du worker ARQ."""

import logging

from src.config import settings
from backend.infrastructure.adapters.arq_job_queue_adapter import parse_redis_settings
from backend.worker.container import WorkerContainer
from backend.worker.tasks import process_document
from backend.worker.use_cases.process_document import ProcessDocumentUseCase

logger = logging.getLogger(__name__)


async def startup(ctx: dict) -> None:
    """Initialise les dependances du worker au demarrage."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    container = WorkerContainer()
    broker = container.event_broker()
    await broker.connect()

    ctx["process_use_case"] = ProcessDocumentUseCase(
        repo=container.document_repository(),
        storage=container.file_storage(),
        event_broker=broker,
        vector_store=container.vector_store(),
    )
    ctx["broker"] = broker
    logger.info("Worker dependencies initialized")


async def shutdown(ctx: dict) -> None:
    """Nettoie les ressources du worker a l'arret."""
    await ctx["broker"].disconnect()
    logger.info("Worker shut down")


class WorkerSettings:
    """Configuration ARQ du worker de vectorisation."""

    functions = [process_document]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = parse_redis_settings(settings.REDIS_URL)
    max_jobs = 5
    job_timeout = 600  # 10 minutes
