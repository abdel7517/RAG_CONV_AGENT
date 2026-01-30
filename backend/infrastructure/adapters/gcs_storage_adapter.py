"""Adapter Google Cloud Storage pour le stockage de fichiers PDF."""

import asyncio
import json
import logging
from google.cloud import storage
from google.oauth2 import service_account

from backend.domain.ports.file_storage_port import FileStoragePort

logger = logging.getLogger(__name__)


class GCSFileStorageAdapter(FileStoragePort):
    """
    Implementation du FileStoragePort utilisant Google Cloud Storage.

    Le bucket est organise par company_id:
        gs://{bucket_name}/{company_id}/{document_id}.pdf

    Authentification (par ordre de priorite):
    1. service_account_key (JSON string depuis .env)
    2. GOOGLE_APPLICATION_CREDENTIALS (variable d'environnement standard)
    3. Default credentials (GCE, Cloud Run, etc.)
    """

    def __init__(
        self,
        bucket_name: str,
        project_id: str = None,
        service_account_key: str = None,
    ):
        credentials = None
        if service_account_key:
            info = json.loads(service_account_key)
            credentials = service_account.Credentials.from_service_account_info(info)

        self._client = storage.Client(
            project=project_id or None,
            credentials=credentials,
        )
        self._bucket = self._client.bucket(bucket_name)
        self._bucket_name = bucket_name

    async def upload(
        self,
        company_id: str,
        document_id: str,
        file_content: bytes,
        content_type: str = "application/pdf",
    ) -> str:
        gcs_path = f"{company_id}/{document_id}.pdf"
        blob = self._bucket.blob(gcs_path)

        await asyncio.to_thread(
            blob.upload_from_string, file_content, content_type=content_type
        )

        logger.info(f"Uploaded {gcs_path} to gs://{self._bucket_name}")
        return gcs_path

    async def delete(self, gcs_path: str) -> bool:
        blob = self._bucket.blob(gcs_path)

        exists = await asyncio.to_thread(blob.exists)
        if exists:
            await asyncio.to_thread(blob.delete)
            logger.info(f"Deleted {gcs_path} from gs://{self._bucket_name}")
            return True
        return False

