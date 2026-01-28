"""
Retriever pour la recherche de documents pertinents.
"""

import logging
from typing import List

from langchain_core.documents import Document

from src.config.settings import settings
from src.retrieval.vector_store import VectorStore

logger = logging.getLogger(__name__)


class Retriever:
    """
    Wrapper autour du VectorStore pour la recherche de documents.
    Supporte le filtrage par company_id pour le multi-tenant.
    """

    def __init__(self, vector_store: VectorStore = None, k: int = None, company_id: str = None):
        self.vector_store = vector_store or VectorStore()
        self.k = k or settings.RETRIEVER_K
        self.company_id = company_id  # company_id par défaut pour l'instance

    def retrieve(self, query: str, k: int = None, company_id: str = None) -> List[Document]:
        """
        Recherche les documents pertinents pour une requête.

        Args:
            query: La requête de recherche
            k: Nombre de résultats (optionnel, utilise self.k par défaut)
            company_id: Filtre par entreprise (priorité sur self.company_id)

        Returns:
            Liste des documents pertinents
        """
        k = k or self.k
        cid = company_id or self.company_id  # Priorité au param, sinon instance

        logger.info(f"Recherche: '{query[:100]}...' (company_id={cid})")

        documents = self.vector_store.similarity_search(query, k=k, company_id=cid)

        logger.info(f"  -> {len(documents)} documents trouves")
        return documents

    def retrieve_with_scores(self, query: str, k: int = None, company_id: str = None) -> List[tuple]:
        """
        Recherche avec scores de similarité.

        Args:
            query: La requête de recherche
            k: Nombre de résultats
            company_id: Filtre par entreprise

        Returns:
            Liste de tuples (Document, score)
        """
        k = k or self.k
        cid = company_id or self.company_id
        return self.vector_store.similarity_search_with_score(query, k=k, company_id=cid)

    def format_documents(self, documents: List[Document]) -> str:
        """
        Formate les documents en une chaîne lisible pour le contexte.

        Args:
            documents: Liste de documents

        Returns:
            Chaîne formatée avec les contenus des documents
        """
        if not documents:
            return "Aucun document pertinent trouve."

        formatted_parts = []
        for i, doc in enumerate(documents, 1):
            source = doc.metadata.get("source", "Source inconnue")
            page = doc.metadata.get("page", "?")
            content = doc.page_content.strip()

            formatted_parts.append(
                f"[Document {i}]\n"
                f"Source: {source} (page {page})\n"
                f"Contenu:\n{content}\n"
            )

        return "\n---\n".join(formatted_parts)

    def retrieve_formatted(self, query: str, k: int = None, company_id: str = None) -> str:
        """
        Recherche et retourne les documents formatés.

        Args:
            query: La requête de recherche
            k: Nombre de résultats
            company_id: Filtre par entreprise

        Returns:
            Chaîne formatée avec les documents pertinents
        """
        documents = self.retrieve(query, k, company_id)
        return self.format_documents(documents)
