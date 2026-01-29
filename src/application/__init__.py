"""
Application layer - Services, agents et use cases.

Cette couche contient la logique métier de l'application.
Elle dépend uniquement des ports du domain (pas des implémentations).
"""

__all__ = [
    "SimpleAgent",
    "OllamaConnectionError",
    "DatabaseConnectionError",
    "AgentError",
]
