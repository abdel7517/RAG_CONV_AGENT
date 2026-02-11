"""Fonctions de taches ARQ pour le worker."""

import logging

logger = logging.getLogger(__name__)


async def process_document(ctx: dict, document_id: str, company_id: str, gcs_path: str) -> None:
    """
    Tache ARQ: vectorisation d'un document PDF.

    Delegue au ProcessDocumentUseCase initialise dans le startup du worker.
    """
    logger.info(f"Processing document {document_id} (company={company_id})")
    use_case = ctx["process_use_case"]
    await use_case.execute({
        "document_id": document_id,
        "company_id": company_id,
        "gcs_path": gcs_path,
    })
