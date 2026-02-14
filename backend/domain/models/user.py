"""Modele domain et schemas API pour la gestion des utilisateurs."""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


@dataclass
class User:
    """
    Entite utilisateur du domaine.

    Utiliser User.create() pour creer un nouvel utilisateur.
    Le constructeur direct est reserve a la reconstitution depuis la persistence.
    """

    user_id: str
    email: str
    hashed_password: str
    company_id: str
    full_name: Optional[str] = None
    disabled: bool = False
    created_at: Optional[datetime] = None

    @classmethod
    def create(
        cls,
        email: str,
        hashed_password: str,
        company_id: str,
        full_name: Optional[str] = None,
    ) -> "User":
        """Factory method: cree un nouvel utilisateur avec un UUID."""
        return cls(
            user_id=str(uuid.uuid4()),
            email=email,
            hashed_password=hashed_password,
            company_id=company_id,
            full_name=full_name,
            disabled=False,
        )


# --- Schemas API (Pydantic) ---


class Token(BaseModel):
    """Schema de reponse pour le token JWT."""

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Donnees extraites du token JWT."""

    email: Optional[str] = None
    company_id: Optional[str] = None


class UserCreate(BaseModel):
    """Schema pour la creation d'un utilisateur."""

    email: EmailStr
    password: str
    company_id: str
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    """Schema de reponse pour un utilisateur (sans mot de passe)."""

    user_id: str
    email: str
    company_id: str
    full_name: Optional[str] = None
    disabled: bool
    created_at: Optional[str] = None


class UserInDB(BaseModel):
    """Schema interne pour un utilisateur avec mot de passe hashe."""

    user_id: str
    email: str
    hashed_password: str
    company_id: str
    full_name: Optional[str] = None
    disabled: bool = False
    created_at: Optional[datetime] = None
