"""Modeles de donnees pour l'API Chat."""
from pydantic import BaseModel, EmailStr


class ChatRequest(BaseModel):
    """Schema pour la requete de chat."""
    company_id: str  # ID unique de l'entreprise (multi-tenant)
    email: EmailStr
    message: str


class ChatResponse(BaseModel):
    """Schema pour la reponse de chat."""
    status: str
    channel: str
