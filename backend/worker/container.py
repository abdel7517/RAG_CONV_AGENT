"""
Container DI pour le worker de traitement de documents.

Reutilise les memes adapters que le backend FastAPI (GCS, PostgreSQL)
et ajoute les adapters specifiques au worker (PGVector pour vectorisation).

Note: Le worker n'a pas de job_queue provider car ARQ gere la consommation
en interne. Le container fournit uniquement les dependances metier.
"""

from dependency_injector import containers, providers

from src.config import settings
from backend.infrastructure.adapters.broadcast_adapter import BroadcastEventBroker
from backend.infrastructure.adapters.gcs_storage_adapter import GCSFileStorageAdapter
from backend.infrastructure.repositories.document_repository import PostgresDocumentRepository
from src.infrastructure.adapters.pgvector_adapter import PGVectorAdapter


class WorkerContainer(containers.DeclarativeContainer):
    """
    Container DI du worker.

    Regroupe les adapters necessaires pour la vectorisation:
    - Event broker (Redis pub/sub for progress)
    - File storage (GCS - download)
    - Document repository (PostgreSQL)
    - Vector store (PGVector)
    """

    # Event Broker (for SSE progress)
    event_broker = providers.Singleton(
        BroadcastEventBroker,
        url=settings.REDIS_URL,
    )

    # File Storage
    file_storage = providers.Singleton(
        GCSFileStorageAdapter,
        bucket_name=settings.GCS_BUCKET_NAME,
        project_id=settings.GCS_PROJECT_ID,
        service_account_key=settings.GCS_SERVICE_ACCOUNT_KEY,
    )

    # Document Repository
    document_repository = providers.Singleton(
        PostgresDocumentRepository,
    )

    # Vector Store
    vector_store = providers.Singleton(
        PGVectorAdapter,
    )
