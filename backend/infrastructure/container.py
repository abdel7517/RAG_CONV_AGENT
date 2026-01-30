"""
Container DI declaratif pour le backend FastAPI.

Utilise dependency-injector pour le wiring automatique avec @inject,
comme dans src/infrastructure/container.py.

Documentation: https://python-dependency-injector.ets-labs.org/
"""

from dependency_injector import containers, providers

from src.config import settings
from backend.infrastructure.adapters.broadcast_adapter import BroadcastEventBroker
from backend.infrastructure.adapters.gcs_storage_adapter import GCSFileStorageAdapter
from backend.infrastructure.adapters.pypdf_analyzer_adapter import PypdfAnalyzerAdapter
from backend.infrastructure.repositories.document_repository import PostgresDocumentRepository


class Container(containers.DeclarativeContainer):
    """
    Container DI du backend.

    Usage Production:
        container = Container()
        broker = container.event_broker()

    Usage Tests (override sans modifier le code):
        with container.event_broker.override(mock_broker):
            # Les routes utilisent le mock
    """

    wiring_config = containers.WiringConfiguration(
        modules=[
            "backend.routes.chat",
            "backend.routes.stream",
            "backend.routes.documents",
        ]
    )

    # =========================================================================
    # EVENT BROKER
    # =========================================================================

    event_broker = providers.Singleton(
        BroadcastEventBroker,
        url=settings.REDIS_URL,
    )
    """
    Broker d'evenements (Singleton).
    Une seule connexion Redis partagee par toute l'application.
    """

    # =========================================================================
    # DOCUMENT MANAGEMENT
    # =========================================================================

    file_storage = providers.Singleton(
        GCSFileStorageAdapter,
        bucket_name=settings.GCS_BUCKET_NAME,
        project_id=settings.GCS_PROJECT_ID,
        service_account_key=settings.GCS_SERVICE_ACCOUNT_KEY,
    )
    """Stockage GCS (Singleton). Une seule connexion au bucket."""

    document_repository = providers.Singleton(
        PostgresDocumentRepository,
    )
    """Repository metadonnees documents (Singleton)."""

    pdf_analyzer = providers.Singleton(
        PypdfAnalyzerAdapter,
    )
    """Analyseur PDF pour le comptage de pages (Singleton)."""
