"""
Port (Interface) pour les LLM providers.

Ce port définit le contrat que tout adapter LLM doit implémenter
(Ollama, Mistral, OpenAI, etc.).
"""

from abc import ABC, abstractmethod

from langchain_core.language_models.chat_models import BaseChatModel


class LLMPort(ABC):
    """
    Interface pour les LLM providers.

    Implémentations possibles:
    - OllamaAdapter (local)
    - MistralAdapter (API)
    - OpenAIAdapter (API)
    - MockLLMAdapter (pour les tests)
    """

    @abstractmethod
    def get_llm(self) -> BaseChatModel:
        """
        Retourne l'instance LLM LangChain configurée.

        Returns:
            Instance BaseChatModel LangChain (ChatOllama, ChatMistralAI, etc.)

        Raises:
            ConnectionError: Si le provider n'est pas accessible
            ConfigurationError: Si la configuration est invalide
        """
        pass

    @abstractmethod
    def check_connection(self) -> bool:
        """
        Vérifie que le provider est accessible.

        Returns:
            True si le provider répond, False sinon
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Retourne le nom du provider (pour les logs)."""
        pass
