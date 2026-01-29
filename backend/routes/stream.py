"""Route GET /stream/{email} - SSE pour recevoir les reponses."""
import asyncio
import json

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse
from dependency_injector.wiring import inject, Provide

from backend.domain.ports.event_broker_port import EventBrokerPort
from backend.infrastructure.container import Container

router = APIRouter()

HEARTBEAT_INTERVAL = 30  # secondes


@router.get("/stream/{email}")
@inject
async def stream_response(
    email: str,
    broker: EventBrokerPort = Depends(Provide[Container.event_broker]),
):
    """
    SSE endpoint pour recevoir les reponses de l'agent en streaming.

    Le client se connecte a ce endpoint et recoit les chunks de reponse
    au fur et a mesure qu'ils sont publies sur outbox:{email}.
    """
    async def event_generator():
        channel = f"outbox:{email}"

        async with broker.subscribe(channel=channel) as subscription:
            while True:
                try:
                    raw = await asyncio.wait_for(
                        subscription.get(),
                        timeout=HEARTBEAT_INTERVAL
                    )

                    data = json.loads(raw)
                    yield {"event": "message", "data": json.dumps(data)}

                    if data.get("done", False):
                        break

                except asyncio.TimeoutError:
                    yield {"event": "heartbeat", "data": ""}
                except Exception as e:
                    yield {
                        "event": "error",
                        "data": json.dumps({"error": str(e)})
                    }
                    break

    return EventSourceResponse(event_generator())
