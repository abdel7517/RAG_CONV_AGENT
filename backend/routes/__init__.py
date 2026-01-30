"""Routes API."""
from .chat import router as chat_router
from .stream import router as stream_router
from .documents import router as documents_router

__all__ = ["chat_router", "stream_router", "documents_router"]
