"""
Adapter PGVector - Implementation du VectorStorePort avec PostgreSQL/pgvector.

Utilise PostgreSQL avec l'extension pgvector pour stocker et rechercher les embeddings.
Le provider d'embedding est configurable via EMBEDDING_PROVIDER (ollama, mistral, openai, huggingface).
"""

import logging
from typing import List, Optional, Tuple, Any

from langchain_core.documents import Document
from langchain_postgres import PGVector
from langchain_postgres.vectorstores import PGVector as PGVectorStore

from src.config.settings import settings
from src.domain.ports.vector_store_port import VectorStorePort
from src.domain.ports.retriever_port import RetrieverPort

logger = logging.getLogger(__name__)


class PGVectorAdapter(VectorStorePort, RetrieverPort):
    """
    Implementation de VectorStorePort utilisant PGVector (PostgreSQL + pgvector).

    Usage:
        adapter = PGVectorAdapter()
        docs = adapter.similarity_search("query", company_id="techstore")

    Tests:
        mock_store = Mock(spec=VectorStorePort)
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
        logger.debug("PGVectorAdapter initialise")

    def _get_embeddings(self):
        """Retourne le modele d'embeddings selon le provider configure (EMBEDDING_PROVIDER)."""
        if self._embeddings is None:
            provider = settings.EMBEDDING_PROVIDER
            if provider == "ollama":
                from langchain_ollama import OllamaEmbeddings
                self._embeddings = OllamaEmbeddings(
                    model=settings.OLLAMA_EMBEDDING_MODEL,
                    base_url=settings.OLLAMA_BASE_URL
                )
                logger.info(f"Utilisation des embeddings Ollama: {settings.OLLAMA_EMBEDDING_MODEL}")
            elif provider == "openai":
                from langchain_openai import OpenAIEmbeddings
                self._embeddings = OpenAIEmbeddings(
                    model=settings.OPENAI_EMBEDDING_MODEL,
                    api_key=settings.OPENAI_API_KEY
                )
                logger.info(f"Utilisation des embeddings OpenAI: {settings.OPENAI_EMBEDDING_MODEL}")
            elif provider == "huggingface":
                from langchain_huggingface import HuggingFaceEmbeddings
                self._embeddings = HuggingFaceEmbeddings(
                    model_name=settings.HUGGINGFACE_EMBEDDING_MODEL
                )
                logger.info(f"Utilisation des embeddings HuggingFace: {settings.HUGGINGFACE_EMBEDDING_MODEL}")
            else:  # mistral par defaut
                from langchain_mistralai import MistralAIEmbeddings
                self._embeddings = MistralAIEmbeddings(
                    model=settings.MISTRAL_EMBEDDING_MODEL,
                    api_key=settings.MISTRAL_API_KEY
                )
                logger.info(f"Utilisation des embeddings Mistral: {settings.MISTRAL_EMBEDDING_MODEL}")
        return self._embeddings

    def _get_vector_store(self) -> PGVectorStore:
        """Retourne ou cree l'instance du vector store."""
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
        Cree le vector store a partir d'une liste de documents.
        Supprime la collection existante et la recree.
        """
        if not documents:
            logger.warning("Aucun document a indexer")
            return

        logger.info(f"Indexation de {len(documents)} documents dans la collection '{self.collection_name}'")

        self._vector_store = PGVectorStore.from_documents(
            documents=documents,
            embedding=self._get_embeddings(),
            collection_name=self.collection_name,
            connection=self.connection_string,
            use_jsonb=True,
            pre_delete_collection=True
        )

        logger.info(f"Indexation terminee: {len(documents)} documents dans '{self.collection_name}'")

    def similarity_search(
        self,
        query: str,
        k: Optional[int] = None,
        company_id: Optional[str] = None
    ) -> List[Any]:
        """
        Recherche les documents les plus similaires a la requete.

        Args:
            query: Texte de recherche
            k: Nombre de resultats a retourner (defaut: settings.RETRIEVER_K)
            company_id: Filtre multi-tenant
        """
        k = k or settings.RETRIEVER_K
        vector_store = self._get_vector_store()

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
        k: Optional[int] = None,
        company_id: Optional[str] = None
    ) -> List[Tuple[Any, float]]:
        """
        Recherche avec scores de similarite.

        Args:
            query: Texte de recherche
            k: Nombre de resultats
            company_id: Filtre multi-tenant
        """
        k = k or settings.RETRIEVER_K
        vector_store = self._get_vector_store()

        search_kwargs = {"k": k}
        if company_id:
            search_kwargs["filter"] = {"company_id": company_id}

        return vector_store.similarity_search_with_score(query, **search_kwargs)

    def as_retriever(self, k: int = None, company_id: str = None):
        """
        Retourne un retriever LangChain filtre par company_id.

        Args:
            k: Nombre de resultats
            company_id: Filtre multi-tenant
        """
        k = k or settings.RETRIEVER_K
        vector_store = self._get_vector_store()

        search_kwargs = {"k": k}
        if company_id:
            search_kwargs["filter"] = {"company_id": company_id}

        return vector_store.as_retriever(search_kwargs=search_kwargs)

    # =========================================================================
    # RetrieverPort implementation
    # =========================================================================

    def retrieve(
        self,
        query: str,
        k: Optional[int] = None,
        company_id: Optional[str] = None
    ) -> List[Any]:
        """
        Recherche les documents pertinents pour une requete.

        Args:
            query: Requete de recherche
            k: Nombre de resultats (defaut: settings.RETRIEVER_K)
            company_id: Filtre par entreprise

        Returns:
            Liste des documents pertinents
        """
        logger.info(f"Recherche: '{query[:100]}...' (company_id={company_id})")
        documents = self.similarity_search(query, k=k, company_id=company_id)
        logger.info(f"  -> {len(documents)} documents trouves")
        return documents

    def retrieve_with_scores(
        self,
        query: str,
        k: Optional[int] = None,
        company_id: Optional[str] = None
    ) -> List[Tuple[Any, float]]:
        """
        Recherche avec scores de similarite.

        Args:
            query: Requete de recherche
            k: Nombre de resultats
            company_id: Filtre par entreprise

        Returns:
            Liste de tuples (Document, score)
        """
        return self.similarity_search_with_score(query, k=k, company_id=company_id)

    def format_documents(self, documents: List[Any]) -> str:
        """
        Formate les documents en une chaine lisible pour le contexte.

        Args:
            documents: Liste de documents

        Returns:
            Chaine formatee avec les contenus des documents
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

    def retrieve_formatted(
        self,
        query: str,
        k: Optional[int] = None,
        company_id: Optional[str] = None
    ) -> str:
        """
        Recherche et retourne les documents formates.

        Args:
            query: Requete de recherche
            k: Nombre de resultats
            company_id: Filtre par entreprise

        Returns:
            Chaine formatee avec les documents pertinents
        """
        documents = self.retrieve(query, k, company_id)
        return self.format_documents(documents)
