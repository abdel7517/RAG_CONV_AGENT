"""
Tools RAG pour l'agent LangChain/LangGraph.

Ce module définit les "tools" que l'agent peut utiliser pour effectuer
des recherches dans la base de documents vectorielle.

Architecture Hexagonale:
========================
- Le RAGService est créé via Container avec injection des ports
- Le tool est créé via une factory function `create_search_tool()`
- Facilement testable avec des mocks des ports (VectorStorePort, RetrieverPort)

FLUX D'APPEL:
=============
1. L'utilisateur pose une question à l'agent
2. Le LLM analyse la question
3. Le LLM DÉCIDE d'appeler search_documents si nécessaire
4. search_documents() utilise le RAGService injecté (via Container)
5. Le résultat est retourné au LLM pour la réponse finale

Voir docs/RAG_TOOL_FLOW.md pour plus de détails.
"""

import logging
from typing import Optional, TYPE_CHECKING

from langchain.tools import tool, ToolRuntime
from langgraph.prebuilt.chat_agent_executor import AgentState  # Contient messages ET remaining_steps

if TYPE_CHECKING:
    from src.application.services.rag_service import RAGService

logger = logging.getLogger(__name__)


# ============================================================================
# ÉTAT PERSONNALISÉ POUR LE MULTI-TENANT
# ============================================================================

class RAGAgentState(AgentState):
    """
    État personnalisé avec company_id et rag_context.

    Utilisé avec state_schema dans create_agent() pour:
    - company_id: Filtrage multi-tenant
    - rag_context: Contexte documentaire récupéré de la DB (RAG Direct)
    """
    company_id: Optional[str]
    rag_context: Optional[str]  # Contexte RAG injecté avant l'appel LLM


# ============================================================================
# FACTORY POUR LE TOOL (Injection de dépendances via closure)
# ============================================================================

def create_search_tool(rag_service: "RAGService"):
    """
    Factory qui crée le tool search_documents avec RAGService injecté.

    Pattern: Closure pour injection de dépendance dans un @tool.
    Le RAGService est capturé dans la closure, éliminant le besoin
    d'une variable globale.

    Args:
        rag_service: Instance de RAGService pour la recherche

    Returns:
        Le tool search_documents configuré

    Usage:
        rag_service = RAGService()
        search_tool = create_search_tool(rag_service)
        # Puis: create_agent(tools=[search_tool], ...)

    Tests:
        mock_service = Mock(spec=RAGService)
        search_tool = create_search_tool(mock_service)
        # Le tool utilise le mock
    """

    @tool
    def search_documents(
        query: str,
        runtime: ToolRuntime[None, RAGAgentState]
    ) -> str:
        """
        Recherche des informations pertinentes dans la base de documents.

        Utilisez cet outil pour trouver des informations sur les produits,
        services, politiques ou toute autre question nécessitant une recherche
        dans la documentation.

        Args:
            query: La question ou les mots-clés à rechercher

        Returns:
            Les extraits de documents pertinents formatés
        """
        # Récupère le company_id depuis l'état injecté via ToolRuntime
        company_id = runtime.state.get("company_id")

        logger.info(f"search_documents: query='{query[:50]}...', company_id={company_id}")

        try:
            result = rag_service.search_formatted(query, company_id=company_id)
            logger.debug(f"Résultat: {len(result)} caractères")
            return result

        except Exception as e:
            logger.error(f"Erreur lors de la recherche: {e}")
            return f"Erreur lors de la recherche dans les documents: {str(e)}"

    return search_documents
