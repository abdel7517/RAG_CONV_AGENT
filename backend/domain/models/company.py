"""Modele domain pour les entreprises (multi-tenant)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Company:
    """
    Entite entreprise du domaine.

    Chaque entreprise a une API key unique pour authentifier
    les widgets chatbot integres sur leurs sites.
    """

    company_id: str
    name: str
    api_key: str
    tone: str = "professionnel et courtois"
    plan: str = "free"
    created_at: Optional[datetime] = None
