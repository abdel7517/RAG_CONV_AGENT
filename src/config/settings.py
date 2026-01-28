"""
Configuration centralisee pour le projet RAG Conversational Agent

Ce fichier charge toutes les variables d'environnement et fournit
une interface unique pour acceder a la configuration.
"""

import os
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()


class Settings:
    """
    Classe de configuration centralisee.
    Toutes les variables d'environnement sont accessibles via cette classe.
    """

    # === CONFIGURATION LLM PROVIDER ===
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")  # "ollama" ou "mistral"
    MODEL_TEMPERATURE: float = float(os.getenv("MODEL_TEMPERATURE", "0.7"))

    # === CONFIGURATION OLLAMA ===
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "phi3:mini")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_EMBEDDING_MODEL: str = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")

    # === CONFIGURATION MISTRAL ===
    MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")
    MISTRAL_MODEL: str = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
    MISTRAL_EMBEDDING_MODEL: str = os.getenv("MISTRAL_EMBEDDING_MODEL", "mistral-embed")

    # === CONFIGURATION POSTGRESQL ===
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "agent_memory")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")

    # === PROMPTS SYSTEME ===
    DEFAULT_SYSTEM_PROMPT: str = (
        "Vous etes un agent de service client francais professionnel et courtois. "
        "Votre role est d'aider les clients avec leurs questions et preoccupations. "
        "Soyez toujours poli, empathique et oriente solution. "
        "Maintenez le contexte de la conversation et fournissez des reponses claires et concises en francais."
    )

    DEFAULT_SYSTEM_PROMPT_RAG: str = (
        "Vous etes un agent de service client francais professionnel et courtois. "
        "Votre role est d'aider les clients avec leurs questions et preoccupations. "
        "Vous avez acces a une base de documents via l'outil 'search_documents'. "
        "Utilisez cet outil pour rechercher des informations pertinentes lorsque les clients posent des questions sur les produits, services ou politiques. "
        "Soyez toujours poli, empathique et oriente solution. "
        "Fournissez des reponses claires basees sur les documents disponibles. "
        "Si l'information n'est pas disponible dans les documents, indiquez-le poliment au client."
    )

    # === TEMPLATE PROMPT RAG PERSONNALISE (Multi-tenant) ===
    DEFAULT_SYSTEM_PROMPT_RAG_TEMPLATE: str = """Tu es un chatbot conversationnel de {company_name}.

CONTEXTE :
Tu assistes les clients UNIQUEMENT sur les sujets lies a {company_name}.
Tu reponds EXCLUSIVEMENT en utilisant les informations recuperees via le tool search_documents.

REGLES OBLIGATOIRES :
1. Utilise TOUJOURS le tool search_documents pour recuperer les informations avant de repondre
2. Reponds UNIQUEMENT avec les donnees retournees par le tool
3. Cite ta source avec [Source: X]
4. Si le tool ne retourne rien de pertinent : "Je n'ai pas cette information dans notre documentation."
5. Si la question est hors sujet : "Desole, je ne peux repondre a cette question."

INTERDICTIONS :
- Ne JAMAIS repondre sans avoir utilise le tool
- Ne JAMAIS inventer ou supposer une information
- Ne JAMAIS repondre a des questions sans rapport avec {company_name}

FORMAT :
- Ton : {tone}
- Reponses concises et structurees

EXEMPLE :
Question : "Quels sont vos delais de livraison ?"
Reponse : D'apres notre documentation, les delais de livraison sont de 2-5 jours ouvres. [Source: CGV]
"""

    SYSTEM_PROMPT: str = os.getenv("SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT)
    SYSTEM_PROMPT_RAG: str = os.getenv("SYSTEM_PROMPT_RAG", os.getenv("SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT_RAG))
    SYSTEM_PROMPT_RAG_TEMPLATE: str = os.getenv("SYSTEM_PROMPT_RAG_TEMPLATE", DEFAULT_SYSTEM_PROMPT_RAG_TEMPLATE)

    @classmethod
    def format_rag_prompt(cls, company_name: str, tone: str) -> str:
        """
        Formate le template RAG avec les infos entreprise.

        Args:
            company_name: Nom de l'entreprise
            tone: Ton du chatbot (ex: "professionnel", "amical")

        Returns:
            Prompt systeme formate
        """
        return cls.SYSTEM_PROMPT_RAG_TEMPLATE.format(
            company_name=company_name,
            tone=tone
        )

    # === CONFIGURATION RAG ===
    DOCUMENTS_PATH: str = os.getenv("DOCUMENTS_PATH", "./documents")
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    RETRIEVER_K: int = int(os.getenv("RETRIEVER_K", "3"))
    PGVECTOR_COLLECTION_NAME: str = os.getenv("PGVECTOR_COLLECTION_NAME", "documents")

    # === CONFIGURATION MESSAGING ===
    CHANNEL_TYPE: str = os.getenv("CHANNEL_TYPE", "redis")  # "redis" ou "memory"
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    @classmethod
    def get_postgres_uri(cls) -> str:
        """
        Construit l'URI de connexion PostgreSQL.
        Priorite a DATABASE_URL si definie.
        """
        return os.getenv(
            "DATABASE_URL",
            f"postgresql://{cls.POSTGRES_USER}:{cls.POSTGRES_PASSWORD}@"
            f"{cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DB}"
        )

    @classmethod
    def get_masked_postgres_uri(cls) -> str:
        """Retourne l'URI avec le mot de passe masque pour l'affichage."""
        uri = cls.get_postgres_uri()
        return uri.replace(cls.POSTGRES_PASSWORD, "***") if cls.POSTGRES_PASSWORD else uri


# Instance globale pour import facile
settings = Settings()
