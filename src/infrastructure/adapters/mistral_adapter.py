"""
Adapter Mistral implémentant LLMPort.

Permet d'utiliser l'API Mistral comme LLM provider via l'architecture hexagonale.
"""

import logging

import httpx
from langchain_core.language_models.chat_models import BaseChatModel

from src.domain.ports.llm_port import LLMPort
from src.config import settings

logger = logging.getLogger(__name__)


class MistralAdapter(LLMPort):
    """
    Adapter pour Mistral AI (API cloud).

    Configuration via settings:
        - MISTRAL_API_KEY: Clé API Mistral
        - MISTRAL_MODEL: Modèle à utiliser (ex: mistral-small-latest)
        - MODEL_TEMPERATURE: Température du modèle
    """

    def __init__(self):
        self._llm = None

    @property
    def provider_name(self) -> str:
        """Retourne le nom du provider."""
        return "mistral"

    def check_connection(self) -> bool:
        """
        Vérifie que l'API Mistral est accessible.

        Returns:
            True si l'API répond, False sinon
        """
        if not settings.MISTRAL_API_KEY:
            logger.warning("MISTRAL_API_KEY non configurée")
            return False

        try:
            response = httpx.get(
                "https://api.mistral.ai/v1/models",
                headers={"Authorization": f"Bearer {settings.MISTRAL_API_KEY}"},
                timeout=10.0
            )
            return response.status_code == 200
        except httpx.RequestError as e:
            logger.warning(f"API Mistral non accessible: {e}")
            return False

    def get_llm(self) -> BaseChatModel:
        """
        Retourne l'instance ChatMistralAI configurée.

        Returns:
            Instance ChatMistralAI LangChain

        Raises:
            ConnectionError: Si l'API n'est pas accessible
            ValueError: Si la clé API n'est pas configurée
        """
        if self._llm is None:
            from langchain_mistralai import ChatMistralAI

            if not settings.MISTRAL_API_KEY:
                raise ValueError(
                    "MISTRAL_API_KEY non configurée. "
                    "Ajoutez-la dans votre fichier .env"
                )

            if not self.check_connection():
                raise ConnectionError(
                    "API Mistral non accessible. "
                    "Vérifiez votre clé API et votre connexion."
                )

            logger.info(f"Initialisation ChatMistralAI: model={settings.MISTRAL_MODEL}")

            self._llm = ChatMistralAI(
                model=settings.MISTRAL_MODEL,
                api_key=settings.MISTRAL_API_KEY,
                temperature=settings.MODEL_TEMPERATURE,
                streaming=True
            )

        return self._llm
