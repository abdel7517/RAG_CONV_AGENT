"""Route POST /chat - Envoi de messages utilisateur."""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from dependency_injector.wiring import inject, Provide
from pydantic import BaseModel

from backend.domain.models.chat import ChatResponse
from backend.domain.ports.event_broker_port import EventBrokerPort
from backend.infrastructure.container import Container
from backend.routes.dependencies import CurrentUser


class ChatMessageRequest(BaseModel):
    """Schema de requete pour envoyer un message."""
    message: str
    email: str

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
@inject
async def send_message(
    request: ChatMessageRequest,
    current_user: CurrentUser,
    broker: EventBrokerPort = Depends(Provide[Container.event_broker]),
):
    """
    Envoie un message utilisateur vers l'agent.

    Le message est publie sur le channel inbox:{email} pour etre
    traite par le worker. L'email et company_id sont extraits du token JWT.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Le message ne peut pas etre vide")

    user_email = request.email
    channel = f"inbox:{user_email}"

    payload = json.dumps({
        "company_id": current_user.company_id,
        "email": user_email,
        "message": request.message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    await broker.publish(channel=channel, message=payload)

    return ChatResponse(
        status="queued",
        channel=f"outbox:{user_email}"
    )
