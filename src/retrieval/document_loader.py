"""
Document Loader pour charger et traiter les fichiers PDF.
"""

import logging
from pathlib import Path
from typing import List

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from src.config.settings import settings

logger = logging.getLogger(__name__)


class DocumentLoader:
    """
    Charge et traite les documents PDF pour le RAG.
    """

    def __init__(
        self,
        documents_path: str = None,
        chunk_size: int = None,
        chunk_overlap: int = None
    ):
        self.documents_path = Path(documents_path or settings.DOCUMENTS_PATH)
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )

    def load_pdf(self, file_path: Path) -> List[Document]:
        """Charge un fichier PDF et retourne les documents."""
        logger.info(f"Chargement du PDF: {file_path}")
        try:
            loader = PyPDFLoader(str(file_path))
            documents = loader.load()
            logger.info(f"  -> {len(documents)} pages chargees")
            return documents
        except Exception as e:
            logger.error(f"Erreur lors du chargement de {file_path}: {e}")
            return []

    def load_all_pdfs(self) -> List[Document]:
        """Charge tous les PDFs du dossier documents."""
        if not self.documents_path.exists():
            logger.warning(f"Le dossier {self.documents_path} n'existe pas")
            return []

        pdf_files = list(self.documents_path.glob("**/*.pdf"))
        logger.info(f"Trouvé {len(pdf_files)} fichiers PDF dans {self.documents_path}")

        all_documents = []
        for pdf_file in pdf_files:
            documents = self.load_pdf(pdf_file)
            all_documents.extend(documents)

        logger.info(f"Total: {len(all_documents)} documents charges")
        return all_documents

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Découpe les documents en chunks."""
        if not documents:
            return []

        chunks = self.text_splitter.split_documents(documents)
        logger.info(f"Documents decoupes en {len(chunks)} chunks")
        return chunks

    def load_and_split(self, company_id: str = None) -> List[Document]:
        """
        Charge tous les PDFs et les découpe en chunks.

        Args:
            company_id: Si fourni, ajoute company_id aux metadata de chaque chunk
                       pour le filtrage multi-tenant.

        Returns:
            Liste des chunks avec metadata enrichies
        """
        documents = self.load_all_pdfs()
        chunks = self.split_documents(documents)

        # Ajouter company_id aux metadata pour le filtrage multi-tenant
        if company_id:
            logger.info(f"Ajout du company_id '{company_id}' aux {len(chunks)} chunks")
            for chunk in chunks:
                chunk.metadata["company_id"] = company_id

        return chunks
