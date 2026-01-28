"""
Container DI déclaratif avec dependency-injector.

Ce module utilise la librairie dependency-injector pour:
- Providers déclaratifs (Singleton, Factory)
- Override pour tests sans modifier le code
- Wiring automatique avec @inject

Documentation: https://python-dependency-injector.ets-labs.org/
"""

import logging

from dependency_injector import containers, providers

from src.infrastructure.adapters.pgvector_adapter import PGVectorAdapter
from src.infrastructure.adapters.langchain_retriever_adapter import LangChainRetrieverAdapter
from src.application.services.rag_service import RAGService
from src.tools.rag_tools import create_search_tool

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
        modules=["src.agents.simple_agent"]
    )

    # =========================================================================
    # ADAPTERS (Singleton pour réutiliser les connexions DB)
    # =========================================================================

    vector_store = providers.Singleton(PGVectorAdapter)
    """
    Adapter PGVector (Singleton).
    Une seule connexion au vector store partagée.
    """

    retriever = providers.Singleton(
        LangChainRetrieverAdapter,
        vector_store=vector_store
    )
    """
    Adapter Retriever (Singleton).
    Dépend du vector_store qui est injecté automatiquement.
    """

    # =========================================================================
    # SERVICES
    # =========================================================================

    rag_service = providers.Singleton(
        RAGService,
        retriever=retriever
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
                    └── retriever
                            └── vector_store
    """
