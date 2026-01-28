"""
Agent conversationnel simple avec LangChain
Base sur la documentation: https://docs.langchain.com/oss/python/langchain/agents
Supporte Ollama (local), Mistral (API) et OpenAI (API) via injection de dépendances.
"""

import asyncio
import logging
from typing import TYPE_CHECKING

import httpx
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from dependency_injector.wiring import inject, Provide

from src.config import settings
from src.infrastructure.container import Container
from src.application.services.rag_service import RAGService
from src.domain.ports.llm_port import LLMPort

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
    - La generation de texte via Ollama (local), Mistral (API) ou OpenAI (API)
    - La persistance des conversations via PostgreSQL
    - Le streaming des reponses token par token

    Architecture Hexagonale:
    =======================
    Le LLM est injecté via le pattern @inject + Provide[].
    Le provider est sélectionné automatiquement selon settings.LLM_PROVIDER
    via providers.Selector dans le Container.
    """

    def __init__(self, enable_rag: bool = False):
        """
        Initialise l'agent avec la configuration centralisee.

        Args:
            enable_rag: Si True, active le RAG avec recherche de documents
        """
        self.enable_rag = enable_rag
        self.llm = None
        self.llm_adapter = None  # LLMPort injecté
        self.agent = None
        self.checkpointer_ctx = None
        self.memory = None
        self._initialized = False

        # Composants RAG (initialises si enable_rag=True)
        self.rag_service = None  # RAGService encapsule VectorStore + Retriever
        self.search_tool = None

        # Cache d'agents par company_id (pour prompts personnalises)
        self._agents_cache: dict = {}

    @inject
    def _init_llm(self, llm_adapter: LLMPort = Provide[Container.llm]):
        """
        Initialise le LLM via injection de dépendances.

        L'adapter LLM est sélectionné automatiquement par le Container
        selon la valeur de settings.LLM_PROVIDER (ollama, mistral, openai).

        Args:
            llm_adapter: Adapter LLM injecté (OllamaAdapter, MistralAdapter ou OpenAIAdapter)

        Raises:
            ConnectionError: Si le provider n'est pas accessible
            ValueError: Si la configuration est invalide (ex: API key manquante)
        """
        self.llm_adapter = llm_adapter
        logger.info(f"Initialisation LLM via {llm_adapter.provider_name} adapter...")
        self.llm = llm_adapter.get_llm()
        logger.info(f"LLM initialisé avec {llm_adapter.provider_name}")

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

    @inject
    def _setup_rag(
        self,
        rag_service: RAGService = Provide[Container.rag_service],
        search_tool=Provide[Container.search_tool]
    ):
        """
        Configure les composants RAG si enable_rag=True.

        Architecture Hexagonale avec @inject:
        =====================================
        RAGService et search_tool sont injectés automatiquement via Provide[].
        Le wire() dans main.py connecte le container à ce module.

        Flow:
            main.py wire() → @inject détecte Provide[] → container résout les dépendances
        """
        if not self.enable_rag:
            return

        logger.info("Configuration RAG avec @inject...")


        self.rag_service = rag_service
        self.search_tool = search_tool

        logger.info("RAG configuré avec @inject")

    async def _setup_company_context(self, company_id: str) -> None:
        """
        Configure l'agent personnalise pour l'entreprise.

        Recupere les infos entreprise depuis PostgreSQL et cree un agent
        avec le prompt personnalise si necessaire.

        Optimisation: Query DB uniquement si l'agent n'est pas deja en cache.

        Args:
            company_id: ID de l'entreprise
        """
        # Si l'agent existe deja dans le cache, pas besoin de query DB
        if company_id in self._agents_cache:
            return

        # Sinon, recuperer les infos entreprise et creer l'agent
        from src.repositories.company_repository import CompanyRepository

        repo = CompanyRepository()
        company = await repo.get_by_id(company_id)

        if company:
            logger.info(f"Creation agent personnalise pour {company.name} ({company_id})")
            self._create_agent_for_company(company.name, company.tone, company_id)
        else:
            logger.warning(f"Entreprise inconnue: {company_id}, utilisation du prompt par defaut")

    def _create_agent_for_company(self, company_name: str, tone: str, company_id: str) -> None:
        """
        Cree un agent avec un prompt personnalise pour une entreprise.

        Args:
            company_name: Nom de l'entreprise
            tone: Ton du chatbot
            company_id: ID pour le cache
        """
        from src.tools.rag_tools import RAGAgentState

        try:
            tools = [self.search_tool] if self.search_tool else []

            # Formater le prompt avec les infos entreprise
            system_prompt = settings.format_rag_prompt(company_name, tone)

            agent = create_agent(
                model=self.llm,
                tools=tools,
                system_prompt=system_prompt,
                state_schema=RAGAgentState,  # Schema d'etat avec company_id pour InjectedState
                checkpointer=self.memory
            )

            self._agents_cache[company_id] = agent
            logger.info(f"Agent personnalise cree pour {company_name}")

        except Exception as e:
            logger.error(f"Erreur creation agent pour {company_id}: {e}")
            # Fallback sur l'agent par defaut
            self._agents_cache[company_id] = self.agent

    def _get_current_agent(self, company_id: str = None):
        """
        Retourne l'agent approprie selon le company_id.

        Args:
            company_id: ID de l'entreprise (passe explicitement pour etre thread-safe)

        Returns:
            L'agent personnalise si disponible, sinon l'agent par defaut
        """
        if company_id and company_id in self._agents_cache:
            return self._agents_cache[company_id]
        return self.agent

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
            # Import conditionnel pour éviter import circulaire
            state_schema = None
            if self.enable_rag:
                from src.tools.rag_tools import RAGAgentState
                state_schema = RAGAgentState

            self.agent = create_agent(
                model=self.llm,
                tools=tools,
                system_prompt=system_prompt,
                state_schema=state_schema,  # Schema avec company_id pour le filtrage multi-tenant
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

    async def chat(self, user_input: str, thread_id: str = "conversation-1", company_id: str = None):
        """
        Envoie un message et stream la reponse.

        Args:
            user_input: Message de l'utilisateur
            thread_id: Identifiant de la conversation
            company_id: ID de l'entreprise pour le filtrage multi-tenant (optionnel)

        Yields:
            str: Tokens de la reponse au fur et a mesure

        Raises:
            AgentError: Si l'agent n'est pas initialise ou si une erreur survient
        """
        logger.debug(f"chat() appelee - user_input: {user_input[:100]}..., thread_id: {thread_id}, company_id: {company_id}")

        if not self._initialized:
            logger.debug("Agent non initialise - levee d'exception")
            raise AgentError("L'agent n'est pas initialise. Appelez initialize() d'abord.")

        config = {"configurable": {"thread_id": thread_id}}
        logger.debug(f"Configuration agent: {config}")
        provider_name = self.llm_adapter.provider_name if self.llm_adapter else "unknown"
        logger.debug(f"Demarrage du streaming avec le LLM provider: {provider_name}")

        # Preparer l'etat avec company_id pour InjectedState
        input_state = {"messages": [HumanMessage(content=user_input)]}
        if company_id:
            input_state["company_id"] = company_id

        try:
            # Utiliser l'agent personnalise si disponible (multi-tenant)
            current_agent = self._get_current_agent(company_id)
            logger.debug("Appel de agent.astream()...")
            async for message_chunk, _ in current_agent.astream(
                input_state,
                config=config,
                stream_mode="messages"
            ):
                logger.debug(f"Chunk recu - type: {type(message_chunk).__name__}, a du contenu: {bool(message_chunk.content)}")
                if message_chunk.content:
                    yield message_chunk.content
            logger.debug("Streaming termine avec succes")
        except httpx.ConnectError as e:
            logger.debug(f"ConnectError: {e}", exc_info=True)
            provider_name = self.llm_adapter.provider_name if self.llm_adapter else "unknown"
            if provider_name == "ollama":
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

            # Configurer le contexte entreprise pour le RAG (filtrage + prompt personnalise)
            if self.enable_rag and company_id:
                await self._setup_company_context(company_id)

            try:
                async for chunk in self.chat(user_message, thread_id=email, company_id=company_id):
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
