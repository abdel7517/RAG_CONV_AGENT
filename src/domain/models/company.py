"""
Modele Company pour la configuration multi-tenant.
"""

from dataclasses import dataclass
from enum import Enum


class CompanyPlan(str, Enum):
    """Plans disponibles pour les entreprises."""

    FREE = "free"
    PRO = "pro"


@dataclass
class Company:
    """
    Configuration d'une entreprise pour le prompt RAG.

    Attributes:
        company_id: Identifiant unique de l'entreprise
        name: Nom affiche de l'entreprise
        tone: Ton du chatbot (ex: "professionnel", "amical")
        plan: Plan de l'entreprise (FREE, PRO)
    """

    company_id: str
    name: str
    tone: str = "professionnel et courtois"
    plan: CompanyPlan = CompanyPlan.FREE
