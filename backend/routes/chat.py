"""Route POST /chat - Envoi de messages utilisateur."""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from dependency_injector.wiring import inject, Provide

from backend.domain.models.chat import ChatRequest, ChatResponse
from backend.domain.ports.event_broker_port import EventBrokerPort
from backend.infrastructure.container import Container

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
@inject
async def send_message(
    request: ChatRequest,
    broker: EventBrokerPort = Depends(Provide[Container.event_broker]),
):
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

    await broker.publish(channel=channel, message=payload)

    return ChatResponse(
        status="queued",
        channel=f"outbox:{request.email}"
    )
