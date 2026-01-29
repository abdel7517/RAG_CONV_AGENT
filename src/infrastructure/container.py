"""
Container DI déclaratif avec dependency-injector.

Ce module utilise la librairie dependency-injector pour:
- Providers déclaratifs (Singleton, Factory, Selector)
- Override pour tests sans modifier le code
- Wiring automatique avec @inject

Documentation: https://python-dependency-injector.ets-labs.org/
"""

import logging

from dependency_injector import containers, providers

from src.config import settings
from src.infrastructure.adapters.pgvector_adapter import PGVectorAdapter
from src.infrastructure.adapters.ollama_adapter import OllamaAdapter
from src.infrastructure.adapters.mistral_adapter import MistralAdapter
from src.infrastructure.adapters.openai_adapter import OpenAIAdapter
from src.infrastructure.adapters.redis_channel_adapter import RedisMessageChannel
from src.infrastructure.adapters.memory_channel_adapter import InMemoryMessageChannel
from src.infrastructure.adapters.document_loader_adapter import PDFDocumentLoaderAdapter
from src.application.services.rag_service import RAGService
from src.application.services.messaging_service import MessagingService
from src.application.rag_tools import create_search_tool

logger = logging.getLogger(__name__)


class Container(containers.DeclarativeContainer):
    """
    Container DI déclaratif.

    Usage Production:
        container = Container()
        service = container.rag_service()

    Usage Tests (override sans modifier le code):
        with container.retriever.override(mock_retriever):
            service = container.rag_service()
            # Le service utilise le mock

    Changer d'implémentation:
        # Pour utiliser Pinecone au lieu de PGVector:
        # 1. Créer PineconeAdapter qui implémente VectorStorePort
        # 2. Changer: vector_store = providers.Singleton(PineconeAdapter)
    """

    # Configuration du wiring automatique
    wiring_config = containers.WiringConfiguration(
        modules=["src.application.simple_agent"]
    )

    # =========================================================================
    # CONFIGURATION
    # =========================================================================

    config = providers.Configuration()
    """Configuration dynamique pour les sélecteurs."""

    # =========================================================================
    # LLM ADAPTERS
    # =========================================================================

    ollama_adapter = providers.Singleton(OllamaAdapter)
    """Adapter Ollama (LLM local)."""

    mistral_adapter = providers.Singleton(MistralAdapter)
    """Adapter Mistral (API cloud)."""

    openai_adapter = providers.Singleton(OpenAIAdapter)
    """Adapter OpenAI (API cloud)."""

    llm = providers.Selector(
        config.llm_provider,
        ollama=ollama_adapter,
        mistral=mistral_adapter,
        openai=openai_adapter,
    )
    """
    Sélecteur LLM basé sur la configuration.

    Usage:
        container.config.llm_provider.from_value("ollama")
        llm_adapter = container.llm()  # Retourne OllamaAdapter

    Le provider est sélectionné automatiquement selon settings.LLM_PROVIDER
    """

    # =========================================================================
    # VECTOR STORE ADAPTERS
    # =========================================================================

    document_loader = providers.Factory(PDFDocumentLoaderAdapter)
    """
    Factory DocumentLoader.
    Factory (pas Singleton) car documents_path peut varier selon l'appel CLI.
    """

    vector_store = providers.Singleton(PGVectorAdapter)
    """
    Adapter PGVector (Singleton).
    Une seule connexion au vector store partagée.
    """

    # =========================================================================
    # SERVICES
    # =========================================================================

    rag_service = providers.Singleton(
        RAGService,
        retriever=vector_store
    )
    """
    Service RAG (Singleton).
    Dépend du retriever qui est injecté automatiquement.
    """

    # =========================================================================
    # TOOLS
    # =========================================================================

    search_tool = providers.Factory(
        create_search_tool,
        rag_service=rag_service
    )
    """
    Tool de recherche RAG (Factory).
    Créé via create_search_tool() avec rag_service injecté.
    Le décorateur @tool est appliqué à l'intérieur de la factory.

    Graphe de dépendances:
        search_tool
            └── rag_service
                    └── vector_store (PGVectorAdapter)
    """

    # =========================================================================
    # MESSAGING
    # =========================================================================

    redis_channel = providers.Singleton(
        RedisMessageChannel,
        url=settings.REDIS_URL
    )
    """Canal Redis (Singleton)."""

    memory_channel = providers.Singleton(InMemoryMessageChannel)
    """Canal In-Memory (Singleton) - pour tests ou dev local."""

    message_channel = providers.Selector(
        config.channel_type,
        redis=redis_channel,
        memory=memory_channel,
    )
    """
    Sélecteur MessageChannel basé sur la configuration.

    Usage:
        container.config.channel_type.from_value("redis")
        channel = container.message_channel()  # Retourne RedisMessageChannel

    Le canal est sélectionné automatiquement selon settings.CHANNEL_TYPE
    """

    messaging_service = providers.Singleton(
        MessagingService,
        channel=message_channel
    )
    """
    Service de messaging (Singleton).

    Encapsule la logique de canaux (connect, subscribe, publish).
    L'appelant n'a pas à gérer les patterns (inbox:*, outbox:).

    Usage dans l'agent:
        async with messaging_service as messaging:
            async for msg in messaging.listen():
                await messaging.publish_chunk(email, chunk)
    """
