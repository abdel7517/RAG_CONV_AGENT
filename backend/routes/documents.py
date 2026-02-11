"""Routes CRUD pour la gestion des documents PDF."""

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sse_starlette.sse import EventSourceResponse
from dependency_injector.wiring import inject, Provide

from backend.application.use_cases.upload_document import UploadDocumentUseCase
from backend.application.use_cases.list_documents import ListDocumentsUseCase
from backend.application.use_cases.delete_document import DeleteDocumentUseCase
from backend.domain.exceptions import (
    DocumentNotFoundError,
    InvalidFileTypeError,
    FileTooLargeError,
    PageLimitExceededError,
)
from backend.domain.models.document import (
    DocumentResponse,
    DocumentListResponse,
    DocumentUploadResponse,
    DocumentDeleteResponse,
)
from backend.domain.ports.document_repository_port import DocumentRepositoryPort
from backend.domain.ports.event_broker_port import EventBrokerPort
from backend.domain.ports.file_storage_port import FileStoragePort
from backend.domain.ports.job_queue_port import JobQueuePort
from backend.domain.ports.pdf_analyzer_port import PdfAnalyzerPort
from backend.infrastructure.container import Container

logger = logging.getLogger(__name__)

router = APIRouter()

HEARTBEAT_INTERVAL = 30  # secondes


@router.post("/documents/upload", response_model=DocumentUploadResponse)
@inject
async def upload_document(
    company_id: str = Query(..., description="ID de l'entreprise"),
    file: UploadFile = File(...),
    repo: DocumentRepositoryPort = Depends(Provide[Container.document_repository]),
    job_queue: JobQueuePort = Depends(Provide[Container.job_queue]),
    storage: FileStoragePort = Depends(Provide[Container.file_storage]),
    pdf_analyzer: PdfAnalyzerPort = Depends(Provide[Container.pdf_analyzer]),
):
    """Upload un document PDF: valide, upload GCS, enqueue vectorisation."""
    if not company_id.strip():
        raise HTTPException(status_code=400, detail="company_id est obligatoire")

    uc = UploadDocumentUseCase(repo, job_queue, storage, pdf_analyzer)
    try:
        document = await uc.execute(
            company_id=company_id,
            filename=file.filename or "unknown.pdf",
            content=await file.read(),
            content_type=file.content_type,
        )
    except InvalidFileTypeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileTooLargeError as e:
        raise HTTPException(status_code=413, detail=str(e))
    except PageLimitExceededError as e:
        raise HTTPException(status_code=413, detail=str(e))

    return DocumentUploadResponse(
        status="queued",
        document_id=document.document_id,
        filename=document.filename,
    )


@router.get("/documents/progress/{document_id}")
@inject
async def document_progress(
    document_id: str,
    broker: EventBrokerPort = Depends(Provide[Container.event_broker]),
):
    """
    SSE endpoint pour suivre la progression du traitement d'un document.

    Publie des evenements de type 'progress' avec:
    - step: validating, uploading, vectorizing, completed, failed
    - progress: pourcentage 0-100
    - message: description lisible
    - done: true quand le traitement est termine
    """
    async def event_generator():
        channel = f"document_progress:{document_id}"

        async with broker.subscribe(channel=channel) as subscription:
            while True:
                try:
                    raw = await asyncio.wait_for(
                        subscription.get(),
                        timeout=HEARTBEAT_INTERVAL,
                    )

                    data = json.loads(raw)
                    yield {"event": "progress", "data": json.dumps(data)}

                    if data.get("done", False):
                        break

                except asyncio.TimeoutError:
                    yield {"event": "heartbeat", "data": ""}
                except Exception as e:
                    yield {
                        "event": "error",
                        "data": json.dumps({"error": str(e)}),
                    }
                    break

    return EventSourceResponse(event_generator())


@router.get("/documents", response_model=DocumentListResponse)
@inject
async def list_documents(
    company_id: str = Query(..., description="ID de l'entreprise"),
    repo: DocumentRepositoryPort = Depends(Provide[Container.document_repository]),
):
    """Liste tous les documents d'une entreprise."""
    if not company_id.strip():
        raise HTTPException(status_code=400, detail="company_id est obligatoire")

    uc = ListDocumentsUseCase(repo)
    documents = await uc.execute(company_id)

    return DocumentListResponse(
        documents=[
            DocumentResponse(
                document_id=d.document_id,
                company_id=d.company_id,
                filename=d.filename,
                size_bytes=d.size_bytes,
                num_pages=d.num_pages,
                content_type=d.content_type,
                status=d.status,
                error_message=d.error_message,
                uploaded_at=d.uploaded_at.isoformat() if d.uploaded_at else "",
            )
            for d in documents
        ],
        total=len(documents),
    )


@router.delete("/documents/{document_id}", response_model=DocumentDeleteResponse)
@inject
async def delete_document(
    document_id: str,
    company_id: str = Query(..., description="ID de l'entreprise"),
    storage=Depends(Provide[Container.file_storage]),
    repo: DocumentRepositoryPort = Depends(Provide[Container.document_repository]),
    vector_store=Depends(Provide[Container.vector_store]),
):
    """Supprime un document (GCS + metadonnees PostgreSQL + vecteurs)."""
    uc = DeleteDocumentUseCase(storage, repo, vector_store)
    try:
        await uc.execute(document_id, company_id)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document non trouve")

    return DocumentDeleteResponse(
        status="deleted",
        document_id=document_id,
    )
