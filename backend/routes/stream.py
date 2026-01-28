"""Route GET /stream/{email} - SSE pour recevoir les reponses."""
import asyncio
import json

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from ..dependencies import broadcast

router = APIRouter()

HEARTBEAT_INTERVAL = 30  # secondes


@router.get("/stream/{email}")
async def stream_response(email: str):
    """
    SSE endpoint pour recevoir les reponses de l'agent en streaming.

    Le client se connecte a ce endpoint et recoit les chunks de reponse
    au fur et a mesure qu'ils sont publies sur outbox:{email}.
    """
    async def event_generator():
        channel = f"outbox:{email}"

        async with broadcast.subscribe(channel=channel) as subscriber:
            while True:
                try:
                    event = await asyncio.wait_for(
                        subscriber.get(),
                        timeout=HEARTBEAT_INTERVAL
                    )

                    data = json.loads(event.message)
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
