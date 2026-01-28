"""
Tools RAG pour l'agent LangChain/LangGraph.

Ce module définit les "tools" que l'agent peut utiliser pour effectuer
des recherches dans la base de documents vectorielle.

FLUX D'APPEL:
=============
1. L'utilisateur pose une question à l'agent
2. Le LLM (Mistral/Ollama) analyse la question
3. Le LLM DÉCIDE d'appeler search_documents si la question nécessite
   des informations de la documentation
4. search_documents() est exécuté automatiquement par LangGraph
5. Le résultat (documents pertinents) est retourné au LLM
6. Le LLM utilise ce contexte pour formuler sa réponse finale

IMPORTANT: Le LLM décide seul quand appeler le tool, basé sur:
- Le system prompt (SYSTEM_PROMPT_RAG)
- La nature de la question
- Le contexte de la conversation

Voir docs/RAG_TOOL_FLOW.md pour plus de détails.
"""

import logging
from typing import Optional

from langchain_core.tools import tool

from src.retrieval.retriever import Retriever
from src.retrieval.vector_store import VectorStore

logger = logging.getLogger(__name__)

# ============================================================================
# GESTION DU RETRIEVER GLOBAL
# ============================================================================
# On utilise une instance globale pour que le tool (qui est une fonction)
# puisse accéder au retriever configuré par SimpleAgent.
# L'alternative serait d'utiliser des closures, mais c'est plus complexe.
# ============================================================================

_retriever: Optional[Retriever] = None


def get_retriever() -> Retriever:
    """Retourne l'instance globale du retriever."""
    global _retriever
    if _retriever is None:
        # Fallback: crée un retriever par défaut si non configuré
        _retriever = Retriever(VectorStore())
    return _retriever


def set_retriever(retriever: Retriever) -> None:
    """
    Définit l'instance globale du retriever.

    Appelé par create_search_documents_tool() lors de l'initialisation
    de l'agent avec enable_rag=True.
    """
    global _retriever
    _retriever = retriever


# ============================================================================
# GESTION DU COMPANY_ID (MULTI-TENANT)
# ============================================================================
# Le company_id est défini par l'agent avant chaque appel au tool.
# Cela permet de filtrer les documents par entreprise.
# ============================================================================

_current_company_id: Optional[str] = None


def get_current_company_id() -> Optional[str]:
    """Retourne le company_id du contexte courant."""
    return _current_company_id


def set_current_company_id(company_id: str) -> None:
    """
    Définit le company_id pour le contexte courant.

    Appelé par SimpleAgent._handle_message() avant de traiter
    chaque message utilisateur.
    """
    global _current_company_id
    _current_company_id = company_id
    logger.debug(f"company_id défini: {company_id}")


# ============================================================================
# TOOL: search_documents
# ============================================================================
# Le décorateur @tool transforme cette fonction en un "Tool" LangChain.
#
# IMPORTANT: La docstring est CRITIQUE car elle est utilisée par le LLM
# pour comprendre QUAND et COMMENT utiliser le tool.
# ============================================================================

@tool
def search_documents(query: str) -> str:
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
    # Récupère le company_id du contexte courant (défini par l'agent)
    company_id = get_current_company_id()

    logger.info(f"Tool search_documents: query='{query[:100]}...', company_id={company_id}")

    try:
        # 1. Récupère le retriever (configuré par SimpleAgent)
        retriever = get_retriever()

        # 2. Recherche les documents pertinents FILTRÉS par company_id
        #    - retrieve() : recherche vectorielle dans pgvector avec filtre
        #    - format_documents() : formate en texte lisible
        result = retriever.retrieve_formatted(query, company_id=company_id)

        # 3. Le résultat est une string qui sera injectée dans le contexte du LLM
        logger.debug(f"Résultat de la recherche: {len(result)} caractères")
        return result

    except Exception as e:
        logger.error(f"Erreur lors de la recherche: {e}")
        return f"Erreur lors de la recherche dans les documents: {str(e)}"


def create_search_documents_tool(retriever: Retriever = None):
    """
    Factory function pour créer le tool search_documents.

    Appelé par SimpleAgent._setup_rag() lors de l'initialisation.

    Args:
        retriever: Instance du Retriever à utiliser. Si fourni,
                   sera défini comme instance globale pour le tool.

    Returns:
        La fonction search_documents décorée avec @tool

    Usage dans SimpleAgent:
        self.search_tool = create_search_documents_tool(self.retriever)
        # Puis passé à create_agent(tools=[self.search_tool])
    """
    if retriever:
        set_retriever(retriever)

    return search_documents
