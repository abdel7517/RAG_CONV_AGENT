"""
Modele Company pour la configuration multi-tenant.
"""

from dataclasses import dataclass


@dataclass
class Company:
    """
    Configuration d'une entreprise pour le prompt RAG.

    Attributes:
        company_id: Identifiant unique de l'entreprise
        name: Nom affiche de l'entreprise
        tone: Ton du chatbot (ex: "professionnel", "amical")
    """
    company_id: str
    name: str
    tone: str = "professionnel et courtois"
