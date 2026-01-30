"""
FastAPI Application - Agent Conversationnel avec SSE + Redis Pub/Sub

Usage:
    uvicorn backend.main:app --reload --port 8000
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .infrastructure.container import Container
from .routes import chat_router, stream_router, documents_router

container = Container()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application."""
    broker = container.event_broker()
    await broker.connect()
    yield
    await broker.disconnect()


app = FastAPI(
    title="RAG Conversational Agent API",
    description="API pour interagir avec l'agent conversationnel via SSE",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api", tags=["chat"])
app.include_router(stream_router, prefix="/api", tags=["stream"])
app.include_router(documents_router, prefix="/api", tags=["documents"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
