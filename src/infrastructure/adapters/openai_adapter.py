"""
Adapter OpenAI implémentant LLMPort.

Permet d'utiliser l'API OpenAI comme LLM provider via l'architecture hexagonale.
"""

import logging

import httpx
from langchain_core.language_models.chat_models import BaseChatModel

from src.domain.ports.llm_port import LLMPort
from src.config import settings

logger = logging.getLogger(__name__)


class OpenAIAdapter(LLMPort):
    """
    Adapter pour OpenAI (API cloud).

    Configuration via settings:
        - OPENAI_API_KEY: Clé API OpenAI
        - OPENAI_MODEL: Modèle à utiliser (ex: gpt-4o-mini)
        - MODEL_TEMPERATURE: Température du modèle
    """

    def __init__(self):
        self._llm = None

    @property
    def provider_name(self) -> str:
        """Retourne le nom du provider."""
        return "openai"

    def check_connection(self) -> bool:
        """
        Vérifie que l'API OpenAI est accessible.

        Returns:
            True si l'API répond, False sinon
        """
        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY non configurée")
            return False

        try:
            response = httpx.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                timeout=10.0
            )
            return response.status_code == 200
        except httpx.RequestError as e:
            logger.warning(f"API OpenAI non accessible: {e}")
            return False

    def get_llm(self) -> BaseChatModel:
        """
        Retourne l'instance ChatOpenAI configurée.

        Returns:
            Instance ChatOpenAI LangChain

        Raises:
            ConnectionError: Si l'API n'est pas accessible
            ValueError: Si la clé API n'est pas configurée
        """
        if self._llm is None:
            from langchain_openai import ChatOpenAI

            if not settings.OPENAI_API_KEY:
                raise ValueError(
                    "OPENAI_API_KEY non configurée. "
                    "Ajoutez-la dans votre fichier .env"
                )

            if not self.check_connection():
                raise ConnectionError(
                    "API OpenAI non accessible. "
                    "Vérifiez votre clé API et votre connexion."
                )

            logger.info(f"Initialisation ChatOpenAI: model={settings.OPENAI_MODEL}")

            self._llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
                temperature=settings.MODEL_TEMPERATURE,
                streaming=True
            )

        return self._llm
