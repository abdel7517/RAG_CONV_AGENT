"""
Adapter Ollama implémentant LLMPort.

Permet d'utiliser Ollama comme LLM provider via l'architecture hexagonale.
"""

import logging

import httpx
from langchain_core.language_models.chat_models import BaseChatModel

from src.domain.ports.llm_port import LLMPort
from src.config import settings

logger = logging.getLogger(__name__)


class OllamaAdapter(LLMPort):
    """
    Adapter pour Ollama (LLM local).

    Configuration via settings:
        - OLLAMA_BASE_URL: URL du serveur Ollama
        - OLLAMA_MODEL: Modèle à utiliser (ex: phi3:mini)
        - MODEL_TEMPERATURE: Température du modèle
    """

    def __init__(self):
        self._llm = None

    @property
    def provider_name(self) -> str:
        """Retourne le nom du provider."""
        return "ollama"

    def check_connection(self) -> bool:
        """
        Vérifie que le serveur Ollama est accessible.

        Returns:
            True si Ollama répond, False sinon
        """
        try:
            response = httpx.get(
                f"{settings.OLLAMA_BASE_URL}/api/tags",
                timeout=5.0
            )
            return response.status_code == 200
        except httpx.RequestError as e:
            logger.warning(f"Ollama non accessible: {e}")
            return False

    def get_llm(self) -> BaseChatModel:
        """
        Retourne l'instance ChatOllama configurée.

        Returns:
            Instance ChatOllama LangChain

        Raises:
            ConnectionError: Si Ollama n'est pas accessible
        """
        if self._llm is None:
            from langchain_ollama import ChatOllama

            if not self.check_connection():
                raise ConnectionError(
                    f"Ollama non disponible à {settings.OLLAMA_BASE_URL}. "
                    "Vérifiez que le serveur est démarré."
                )

            logger.info(
                f"Initialisation ChatOllama: model={settings.OLLAMA_MODEL}, "
                f"url={settings.OLLAMA_BASE_URL}"
            )

            self._llm = ChatOllama(
                model=settings.OLLAMA_MODEL,
                base_url=settings.OLLAMA_BASE_URL,
                temperature=settings.MODEL_TEMPERATURE,
                streaming=True
            )

        return self._llm
