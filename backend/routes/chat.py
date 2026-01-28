"""Route POST /chat - Envoi de messages utilisateur."""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from ..dependencies import broadcast

router = APIRouter()


class ChatRequest(BaseModel):
    """Schema pour la requete de chat."""
    company_id: str  # ID unique de l'entreprise (multi-tenant)
    email: EmailStr
    message: str


class ChatResponse(BaseModel):
    """Schema pour la reponse de chat."""
    status: str
    channel: str


@router.post("/chat", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """
    Envoie un message utilisateur vers l'agent.

    Le message est publie sur le channel inbox:{email} pour etre
    traite par le worker.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Le message ne peut pas etre vide")

    if not request.company_id.strip():
        raise HTTPException(status_code=400, detail="company_id est obligatoire")

    channel = f"inbox:{request.email}"

    payload = json.dumps({
        "company_id": request.company_id,
        "email": request.email,
        "message": request.message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    await broadcast.publish(channel=channel, message=payload)

    return ChatResponse(
        status="queued",
        channel=f"outbox:{request.email}"
    )
