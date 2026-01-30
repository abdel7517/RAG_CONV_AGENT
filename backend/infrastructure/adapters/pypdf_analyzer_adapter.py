"""Adapter pypdf pour l'analyse de fichiers PDF."""

import io

from pypdf import PdfReader

from backend.domain.ports.pdf_analyzer_port import PdfAnalyzerPort


class PypdfAnalyzerAdapter(PdfAnalyzerPort):
    """Implementation de PdfAnalyzerPort utilisant pypdf."""

    def count_pages(self, content: bytes) -> int:
        reader = PdfReader(io.BytesIO(content))
        return len(reader.pages)
