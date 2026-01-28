"""
Vector Store utilisant PGVector (PostgreSQL) pour stocker les embeddings.
"""

import logging
from typing import List, Optional

from langchain_core.documents import Document
from langchain_postgres import PGVector
from langchain_postgres.vectorstores import PGVector as PGVectorStore

from src.config.settings import settings

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Gestionnaire du vector store PGVector.
    Utilise PostgreSQL avec l'extension pgvector pour stocker et rechercher les embeddings.
    """

    def __init__(
        self,
        collection_name: str = None,
        connection_string: str = None
    ):
        self.collection_name = collection_name or settings.PGVECTOR_COLLECTION_NAME
        self.connection_string = connection_string or settings.get_postgres_uri()
        self._embeddings = None
        self._vector_store: Optional[PGVectorStore] = None

    def _get_embeddings(self):
        """Retourne le modèle d'embeddings selon le provider configuré."""
        if self._embeddings is None:
            if settings.LLM_PROVIDER == "ollama":
                from langchain_ollama import OllamaEmbeddings
                self._embeddings = OllamaEmbeddings(
                    model=settings.OLLAMA_EMBEDDING_MODEL,
                    base_url=settings.OLLAMA_BASE_URL
                )
                logger.info(f"Utilisation des embeddings Ollama: {settings.OLLAMA_EMBEDDING_MODEL}")
            else:
                from langchain_mistralai import MistralAIEmbeddings
                self._embeddings = MistralAIEmbeddings(
                    model=settings.MISTRAL_EMBEDDING_MODEL,
                    api_key=settings.MISTRAL_API_KEY
                )
                logger.info(f"Utilisation des embeddings Mistral: {settings.MISTRAL_EMBEDDING_MODEL}")
        return self._embeddings

    def _get_vector_store(self) -> PGVectorStore:
        """Retourne ou crée l'instance du vector store."""
        if self._vector_store is None:
            self._vector_store = PGVectorStore(
                embeddings=self._get_embeddings(),
                collection_name=self.collection_name,
                connection=self.connection_string,
                use_jsonb=True
            )
        return self._vector_store

    async def create_from_documents(self, documents: List[Document]) -> None:
        """
        Crée le vector store à partir d'une liste de documents.
        Supprime la collection existante et la recrée.
        """
        if not documents:
            logger.warning("Aucun document a indexer")
            return

        logger.info(f"Indexation de {len(documents)} documents dans la collection '{self.collection_name}'")

        # Utiliser la méthode de classe pour créer depuis les documents
        self._vector_store = PGVectorStore.from_documents(
            documents=documents,
            embedding=self._get_embeddings(),
            collection_name=self.collection_name,
            connection=self.connection_string,
            use_jsonb=True,
            pre_delete_collection=True  # Supprime et recrée la collection
        )

        logger.info(f"Indexation terminee: {len(documents)} documents dans '{self.collection_name}'")

    def similarity_search(
        self,
        query: str,
        k: int = None,
        company_id: str = None
    ) -> List[Document]:
        """
        Recherche les documents les plus similaires à la requête.

        Args:
            query: La requête de recherche
            k: Nombre de résultats à retourner (défaut: settings.RETRIEVER_K)
            company_id: Si fourni, filtre les résultats par entreprise

        Returns:
            Liste des documents les plus similaires
        """
        k = k or settings.RETRIEVER_K
        vector_store = self._get_vector_store()

        # Construction des kwargs avec filtre optionnel
        search_kwargs = {"k": k}
        if company_id:
            search_kwargs["filter"] = {"company_id": company_id}

        logger.debug(f"Recherche: '{query[:50]}...' (k={k}, company_id={company_id})")
        results = vector_store.similarity_search(query, **search_kwargs)
        logger.debug(f"  -> {len(results)} resultats trouves")

        return results

    def similarity_search_with_score(
        self,
        query: str,
        k: int = None,
        company_id: str = None
    ) -> List[tuple]:
        """
        Recherche avec scores de similarité.

        Args:
            query: La requête de recherche
            k: Nombre de résultats
            company_id: Si fourni, filtre les résultats par entreprise

        Returns:
            Liste de tuples (Document, score)
        """
        k = k or settings.RETRIEVER_K
        vector_store = self._get_vector_store()

        search_kwargs = {"k": k}
        if company_id:
            search_kwargs["filter"] = {"company_id": company_id}

        results = vector_store.similarity_search_with_score(query, **search_kwargs)
        return results

    def as_retriever(self, k: int = None, company_id: str = None):
        """
        Retourne un retriever LangChain filtré par company_id.

        Args:
            k: Nombre de résultats
            company_id: Si fourni, filtre les résultats par entreprise
        """
        k = k or settings.RETRIEVER_K
        vector_store = self._get_vector_store()

        search_kwargs = {"k": k}
        if company_id:
            search_kwargs["filter"] = {"company_id": company_id}

        return vector_store.as_retriever(search_kwargs=search_kwargs)
