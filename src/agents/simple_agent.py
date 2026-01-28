"""
Agent conversationnel simple avec LangChain
Base sur la documentation: https://docs.langchain.com/oss/python/langchain/agents
Supporte Ollama (local) et Mistral (API)
"""

import asyncio
import logging
from typing import TYPE_CHECKING

import httpx
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from src.config import settings

if TYPE_CHECKING:
    from src.messaging import MessageChannel, Message

logger = logging.getLogger(__name__)


class LLMProviderError(Exception):
    """Erreur liee au provider LLM."""
    pass


class OllamaConnectionError(Exception):
    """Erreur de connexion a Ollama."""
    pass


class DatabaseConnectionError(Exception):
    """Erreur de connexion a la base de donnees."""
    pass


class AgentError(Exception):
    """Erreur generale de l'agent."""
    pass


class SimpleAgent:
    """
    Agent conversationnel simple avec memoire PostgreSQL.

    Cet agent utilise LangChain et LangGraph pour gerer:
    - La generation de texte via Ollama (local) ou Mistral (API)
    - La persistance des conversations via PostgreSQL
    - Le streaming des reponses token par token
    """

    SUPPORTED_PROVIDERS = ["ollama", "mistral"]

    def __init__(self, llm_provider: str = None, enable_rag: bool = False):
        """
        Initialise l'agent avec la configuration centralisee.

        Args:
            llm_provider: Provider LLM a utiliser ("ollama" ou "mistral").
                         Si None, utilise la valeur de LLM_PROVIDER dans .env
            enable_rag: Si True, active le RAG avec recherche de documents
        """
        self.llm_provider = llm_provider or settings.LLM_PROVIDER
        self.enable_rag = enable_rag
        self.llm = None
        self.agent = None
        self.checkpointer_ctx = None
        self.memory = None
        self._initialized = False

        # Composants RAG (initialises si enable_rag=True)
        self.vector_store = None
        self.retriever = None
        self.search_tool = None

    def _check_ollama_connection(self) -> bool:
        """
        Verifie que Ollama est accessible.

        Returns:
            bool: True si Ollama repond, False sinon
        """
        try:
            response = httpx.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5.0)
            return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    def _init_llm_ollama(self):
        """Initialise le LLM avec Ollama."""
        from langchain_ollama import ChatOllama

        if not self._check_ollama_connection():
            raise OllamaConnectionError(
                f"Impossible de se connecter a Ollama sur {settings.OLLAMA_BASE_URL}\n"
                "Assurez-vous qu'Ollama est demarre avec: ollama serve"
            )

        self.llm = ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=settings.MODEL_TEMPERATURE,
            streaming=True
        )

    def _init_llm_mistral(self):
        """Initialise le LLM avec Mistral API."""
        from langchain_mistralai import ChatMistralAI

        if not settings.MISTRAL_API_KEY:
            raise LLMProviderError(
                "MISTRAL_API_KEY n'est pas definie.\n"
                "Ajoutez votre cle API Mistral dans le fichier .env:\n"
                "MISTRAL_API_KEY=votre_cle_api"
            )

        self.llm = ChatMistralAI(
            model=settings.MISTRAL_MODEL,
            api_key=settings.MISTRAL_API_KEY,
            temperature=settings.MODEL_TEMPERATURE,
            streaming=True
        )

    def _init_llm(self):
        """Initialise le modele de langage selon le provider configure."""
        if self.llm_provider == "ollama":
            self._init_llm_ollama()
        elif self.llm_provider == "mistral":
            self._init_llm_mistral()
        else:
            raise LLMProviderError(
                f"Provider LLM inconnu: '{self.llm_provider}'\n"
                f"Providers supportes: {', '.join(self.SUPPORTED_PROVIDERS)}"
            )

    async def _setup_memory(self):
        """Configure la memoire PostgreSQL."""
        try:
            self.checkpointer_ctx = AsyncPostgresSaver.from_conn_string(settings.get_postgres_uri())
            self.memory = await self.checkpointer_ctx.__aenter__()
            await self.memory.setup()
        except Exception as e:
            raise DatabaseConnectionError(
                f"Impossible de se connecter a PostgreSQL: {e}\n"
                "Verifiez que PostgreSQL est demarre et que les credentials sont corrects.\n"
                "Lancez: python main.py setup-db pour plus de details."
            )

    def _setup_rag(self):
        """
        Configure les composants RAG si enable_rag=True.

        Cette méthode initialise la chaîne de composants nécessaires
        pour la recherche de documents:

        VectorStore → Retriever → search_tool
            │             │            │
            │             │            └── Tool LangChain appelable par le LLM
            │             └── Wrapper qui formate les résultats
            └── Connexion à pgvector (PostgreSQL)

        Le tool sera ensuite passé à create_agent() dans _create_agent().
        Voir docs/RAG_TOOL_FLOW.md pour le flux complet.
        """
        if not self.enable_rag:
            return

        from src.retrieval import VectorStore, Retriever
        from src.tools.rag_tools import create_search_documents_tool

        logger.info("Configuration des composants RAG...")

        # 1. VectorStore: interface avec pgvector pour le stockage/recherche vectorielle
        self.vector_store = VectorStore()

        # 2. Retriever: wrapper qui effectue la recherche et formate les résultats
        self.retriever = Retriever(self.vector_store)

        # 3. Tool: fonction décorée @tool que le LLM peut appeler
        #    Le retriever est passé pour être utilisé comme instance globale
        self.search_tool = create_search_documents_tool(self.retriever)

        logger.info("Composants RAG initialises")

    def _create_agent(self):
        """
        Crée l'agent LangGraph avec ou sans RAG.

        L'agent est créé via create_agent() de LangChain qui configure:
        - Le LLM (Mistral ou Ollama)
        - Les tools disponibles (search_documents si RAG activé)
        - Le system prompt qui guide le comportement du LLM
        - Le checkpointer pour la mémoire persistante (PostgreSQL)

        FLUX AVEC RAG:
        ==============
        User message → LLM analyse → LLM décide d'appeler search_documents
                                            ↓
                                   search_documents(query)
                                            ↓
                                   Résultat injecté dans le contexte
                                            ↓
                                   LLM génère la réponse finale
        """
        try:
            # Liste des tools disponibles pour le LLM
            # Si RAG activé: le LLM peut appeler search_documents quand il le juge nécessaire
            # Si RAG désactivé: liste vide, le LLM répond sans recherche de documents
            tools = [self.search_tool] if self.enable_rag and self.search_tool else []

            # Le system prompt guide le comportement du LLM
            # SYSTEM_PROMPT_RAG inclut des instructions pour utiliser le tool de recherche
            system_prompt = settings.SYSTEM_PROMPT_RAG if self.enable_rag else settings.SYSTEM_PROMPT

            # Création de l'agent LangGraph
            # Le LLM décidera automatiquement quand appeler les tools
            self.agent = create_agent(
                model=self.llm,
                tools=tools,
                system_prompt=system_prompt,
                checkpointer=self.memory  # Mémoire PostgreSQL pour persistance
            )

            if self.enable_rag:
                logger.info("Agent cree avec le tool search_documents (RAG actif)")
            else:
                logger.info("Agent cree sans tools (mode simple)")
        except Exception as e:
            raise AgentError(f"Erreur lors de la creation de l'agent: {e}")

    async def initialize(self):
        """
        Initialise tous les composants de l'agent.

        Raises:
            LLMProviderError: Si le provider est inconnu ou mal configure
            OllamaConnectionError: Si Ollama n'est pas accessible
            DatabaseConnectionError: Si PostgreSQL n'est pas accessible
            AgentError: Si la creation de l'agent echoue
        """
        if self._initialized:
            return

        self._init_llm()
        await self._setup_memory()
        self._setup_rag()  # Configure RAG si enable_rag=True
        self._create_agent()
        self._initialized = True

        mode = "RAG" if self.enable_rag else "Simple"
        logger.info(f"Agent initialise en mode {mode}")

    async def chat(self, user_input: str, thread_id: str = "conversation-1"):
        """
        Envoie un message et stream la reponse.

        Args:
            user_input: Message de l'utilisateur
            thread_id: Identifiant de la conversation

        Yields:
            str: Tokens de la reponse au fur et a mesure

        Raises:
            AgentError: Si l'agent n'est pas initialise ou si une erreur survient
        """
        logger.debug(f"chat() appelee - user_input: {user_input[:100]}..., thread_id: {thread_id}")

        if not self._initialized:
            logger.debug("Agent non initialise - levee d'exception")
            raise AgentError("L'agent n'est pas initialise. Appelez initialize() d'abord.")

        config = {"configurable": {"thread_id": thread_id}}
        logger.debug(f"Configuration agent: {config}")
        logger.debug(f"Demarrage du streaming avec le LLM provider: {self.llm_provider}")

        try:
            logger.debug("Appel de agent.astream()...")
            async for message_chunk, _ in self.agent.astream(
                {"messages": [HumanMessage(content=user_input)]},
                config=config,
                stream_mode="messages"
            ):
                logger.debug(f"Chunk recu - type: {type(message_chunk).__name__}, a du contenu: {bool(message_chunk.content)}")
                if message_chunk.content:
                    yield message_chunk.content
            logger.debug("Streaming termine avec succes")
        except httpx.ConnectError as e:
            logger.debug(f"ConnectError: {e}", exc_info=True)
            if self.llm_provider == "ollama":
                raise OllamaConnectionError(
                    "Connexion a Ollama perdue. Verifiez qu'Ollama est toujours en cours d'execution."
                )
            else:
                raise AgentError("Connexion au serveur LLM perdue.")
        except httpx.TimeoutException as e:
            logger.debug(f"TimeoutException: {e}", exc_info=True)
            raise AgentError(
                "Timeout lors de la communication avec le LLM. Le modele met peut-etre trop de temps a repondre."
            )
        except Exception as e:
            logger.debug(f"Exception inattendue - {type(e).__name__}: {e}", exc_info=True)
            raise AgentError(f"Erreur lors de la generation de la reponse: {e}")

    async def serve(
        self,
        channel: "MessageChannel",
        inbox_pattern: str = "inbox:*",
        outbox_prefix: str = "outbox:"
    ):
        """
        Ecoute les messages entrants et repond via le canal.

        Cette methode permet a l'agent de fonctionner en mode serveur,
        ecoutant les messages sur un canal et repondant de maniere asynchrone.

        Args:
            channel: Canal de messages (Redis, In-Memory, etc.)
            inbox_pattern: Pattern pour les messages entrants (defaut: "inbox:*")
            outbox_prefix: Prefixe pour les canaux de sortie (defaut: "outbox:")

        Example:
            >>> from src.messaging import create_channel
            >>> channel = create_channel("redis", url="redis://localhost:6379")
            >>> agent = SimpleAgent()
            >>> await agent.initialize()
            >>> await agent.serve(channel)
        """
        # Auto-initialisation si necessaire
        if not self._initialized:
            logger.info("Auto-initialisation...")
            await self.initialize()

        self._outbox_prefix = outbox_prefix

        await channel.connect()
        await channel.subscribe(inbox_pattern)

        logger.info(f"Agent en ecoute sur {inbox_pattern}...")

        try:
            async for msg in channel.listen():
                asyncio.create_task(
                    self._handle_message(channel, msg)
                )
        finally:
            await channel.disconnect()

    async def _handle_message(self, channel: "MessageChannel", msg: "Message"):
        """
        Traite un message et publie la reponse.

        Args:
            channel: Canal de messages pour publier la reponse
            msg: Message recu a traiter
        """
        try:
            company_id = msg.data.get("company_id")  # Multi-tenant: ID entreprise
            email = msg.data.get("email", "unknown")
            user_message = msg.data.get("message", "")
            outbox = f"{self._outbox_prefix}{email}"

            logger.info(f"Message de {email} (company: {company_id}): {user_message[:50]}...")

            # Définir le company_id pour le tool search_documents (filtrage RAG)
            if self.enable_rag and company_id:
                from src.tools.rag_tools import set_current_company_id
                set_current_company_id(company_id)

            try:
                async for chunk in self.chat(user_message, thread_id=email):
                    logger.debug(f"PUBLISH {outbox}: chunk='{chunk[:50]}...' done=False")
                    await channel.publish(outbox, {"chunk": chunk, "done": False})

                logger.debug(f"PUBLISH {outbox}: chunk='' done=True")
                await channel.publish(outbox, {"chunk": "", "done": True})
                logger.info(f"Reponse complete envoyee a {email}")

            except Exception as e:
                logger.error(f"Erreur lors du traitement: {e}")
                await channel.publish(outbox, {
                    "chunk": f"Erreur: {str(e)}",
                    "done": True
                })

        except KeyError as e:
            logger.error(f"Champ manquant dans le message: {e}")
        except Exception as e:
            logger.error(f"Erreur inattendue: {e}")

    async def cleanup(self):
        """Nettoie les ressources."""
        try:
            if self.checkpointer_ctx:
                await self.checkpointer_ctx.__aexit__(None, None, None)
        except Exception:
            pass  # Ignorer les erreurs de nettoyage
