"""
Services layer - Réexporte depuis application/services pour rétrocompatibilité.

NOTE: L'implémentation a été déplacée vers src/application/services/
dans le cadre de l'architecture hexagonale.
"""

from src.application.services.rag_service import RAGService

__all__ = ["RAGService"]
