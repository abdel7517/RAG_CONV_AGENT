"""
Agent conversationnel simple avec LangChain
Base sur la documentation: https://docs.langchain.com/oss/python/langchain/agents
Supporte Ollama (local), Mistral (API) et OpenAI (API) via injection de dépendances.
"""

import asyncio
import logging
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, ValidationError, Field

import httpx
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from dependency_injector.wiring import inject, Provide

from src.config import settings
from src.infrastructure.container import Container
from src.application.services.rag_service import RAGService
from src.application.services.messaging_service import MessagingService
from src.domain.ports.llm_port import LLMPort

if TYPE_CHECKING:
    from src.domain.ports.message_channel_port import Message

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


class MessageValidationError(Exception):
    """Erreur de validation du message entrant."""
    pass


class _ParsedMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    company_id: str = Field(min_length=1)
    email: str = Field(min_length=1)
    user_message: str = Field(min_length=1, validation_alias="message")

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
        from src.infrastructure.repositories.company_repository import CompanyRepository

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
        from src.application.rag_tools import RAGAgentState

        try:
            tools = [self.search_tool] if self.search_tool else []

            # Prompt statique personnalise pour l'entreprise
            system_prompt = settings.format_rag_prompt(company_name, tone)

            agent = create_react_agent(
                model=self.llm,
                tools=tools,
                prompt=system_prompt,
                state_schema=RAGAgentState,
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
        - Le system prompt (statique ou Callable pour RAG dynamique)
        - Le checkpointer pour la mémoire persistante (PostgreSQL)

        FLUX RAG DIRECT:
        ================
        User message → Recherche DB → rag_context dans state → prompt Callable lit state
                                                                        ↓
                                                               Prompt avec contexte injecté
                                                                        ↓
                                                               LLM génère la réponse
        """
        try:
            # Liste des tools disponibles pour le LLM
            tools = [self.search_tool] if self.enable_rag and self.search_tool else []

            state_schema = None
            prompt = settings.SYSTEM_PROMPT  # Défaut: prompt statique

            if self.enable_rag:
                from src.application.rag_tools import RAGAgentState
                state_schema = RAGAgentState
                prompt = settings.SYSTEM_PROMPT_RAG  # Prompt RAG statique

            self.agent = create_react_agent(
                model=self.llm,
                tools=tools,
                prompt=prompt,
                state_schema=state_schema,
                checkpointer=self.memory
            )

            if self.enable_rag:
                logger.info("Agent cree avec RAG (contexte injecte dans message)")
            else:
                logger.info("Agent cree sans RAG (mode simple)")
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

    def _enrich_with_rag(self, user_input: str, company_id: str = None) -> str | None:
        """
        Enrichit le message avec le contexte RAG si active.

        Returns:
            Le message enrichi, le message original (si RAG desactive),
            ou None si aucun document trouve.
        """
        if not self.enable_rag or not self.rag_service:
            return user_input

        logger.debug(f"RAG: Recherche pour: {user_input[:50]}...")
        rag_context = self.rag_service.search_formatted(user_input, company_id=company_id)

        if not rag_context:
            logger.info(f"RAG: Aucun document pour company_id={company_id}")
            return None

        logger.debug(f"RAG: {len(rag_context)} chars de contexte")
        return f"CONTEXTE DOCUMENTAIRE:\n{rag_context}\n\n---\nQUESTION: {user_input}"

    def _build_input_state(self, message: str, company_id: str = None) -> dict:
        """Construit le state d'entree pour l'agent."""
        state = {"messages": [HumanMessage(content=message)]}
        if company_id:
            state["company_id"] = company_id
        return state

    async def _stream_response(self, input_state: dict, config: dict, company_id: str = None):
        """
        Stream la reponse de l'agent avec gestion d'erreurs.

        Yields:
            str: Tokens de la reponse
        """
        provider_name = self.llm_adapter.provider_name if self.llm_adapter else "unknown"
        current_agent = self._get_current_agent(company_id)

        try:
            async for chunk, _ in current_agent.astream(
                input_state, config=config, stream_mode="messages"
            ):
                if chunk.content:
                    yield chunk.content
        except httpx.ConnectError:
            if provider_name == "ollama":
                raise OllamaConnectionError(
                    "Connexion a Ollama perdue. Verifiez qu'Ollama est toujours en cours d'execution."
                )
            raise AgentError("Connexion au serveur LLM perdue.")
        except httpx.TimeoutException:
            raise AgentError(
                "Timeout lors de la communication avec le LLM. Le modele met peut-etre trop de temps a repondre."
            )
        except Exception as e:
            raise AgentError(f"Erreur lors de la generation de la reponse: {e}")

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
        if not self._initialized:
            raise AgentError("L'agent n'est pas initialise. Appelez initialize() d'abord.")

        message = self._enrich_with_rag(user_input, company_id)
        if message is None:
            yield "Je n'ai pas cette information dans notre documentation."
            return

        input_state = self._build_input_state(message, company_id)
        config = {"configurable": {"thread_id": thread_id}}

        logger.debug(f"chat({user_input[:50]}...) -> thread={thread_id}, company={company_id}")

        async for chunk in self._stream_response(input_state, config, company_id):
            yield chunk

    @inject
    async def serve(
        self,
        messaging: MessagingService = Provide[Container.messaging_service]
    ):
        """
        Ecoute les messages entrants et repond via le service de messaging.

        Cette methode permet a l'agent de fonctionner en mode serveur,
        ecoutant les messages sur un canal et repondant de maniere asynchrone.

        Architecture Hexagonale avec @inject:
        =====================================

        Args:
            messaging: Service de messaging injecté
        """
        # Auto-initialisation si necessaire
        if not self._initialized:
            logger.info("Auto-initialisation...")
            await self.initialize()

        async with messaging:
            logger.info("Agent en écoute...")
            async for msg in messaging.listen():
                asyncio.create_task(
                    self._handle_message(messaging, msg)
                )

    async def _ensure_company_context(self, company_id: str | None) -> None:
        """
        Configure le contexte entreprise si le RAG est actif et un company_id est fourni.

        Args:
            company_id: ID de l'entreprise (None si pas de multi-tenant)
        """
        if self.enable_rag and company_id:
            await self._setup_company_context(company_id)

    async def _stream_response_to_user(
        self, messaging: MessagingService, parsed: _ParsedMessage
    ) -> None:
        """
        Execute le chat en streaming et publie les chunks vers l'utilisateur.

        Args:
            messaging: Service de messaging pour publier la reponse
            parsed: Message parse et valide
        """
        async for chunk in self.chat(
            parsed.user_message,
            thread_id=parsed.email,
            company_id=parsed.company_id,
        ):
            await messaging.publish_chunk(parsed.email, chunk)

        await messaging.publish_chunk(parsed.email, "", done=True)

    async def _handle_message(self, messaging: MessagingService, msg: "Message"):
        """
        Traite un message et publie la reponse.

        Pipeline:
            1. Parse et validation du message
            2. Configuration du contexte entreprise (si multi-tenant)
            3. Streaming de la reponse vers l'utilisateur

        Args:
            messaging: Service de messaging pour publier la reponse
            msg: Message recu a traiter
        """
        try:
            parsed = _ParsedMessage(**msg.data)
        except ValidationError as e:
            logger.warning(f"Message invalide: {e}")
            return

        logger.info(
            f"Message de {parsed.email} (company: {parsed.company_id}): "
            f"{parsed.user_message[:50]}..."
        )

        try:
            await self._ensure_company_context(parsed.company_id)
            await self._stream_response_to_user(messaging, parsed)

        except (AgentError, OllamaConnectionError) as e:
            logger.error(f"Erreur agent pour {parsed.email}: {e}")
            await messaging.publish_error(parsed.email, str(e))

        except Exception as e:
            logger.error(f"Erreur inattendue pour {parsed.email}: {e}", exc_info=True)
            await messaging.publish_error(parsed.email, "Une erreur inattendue est survenue.")

    async def cleanup(self):
        """Nettoie les ressources."""
        try:
            if self.checkpointer_ctx:
                await self.checkpointer_ctx.__aexit__(None, None, None)
        except Exception:
            pass  # Ignorer les erreurs de nettoyage
