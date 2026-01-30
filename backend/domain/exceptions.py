"""Exceptions domain pour la gestion des documents."""


class DocumentNotFoundError(Exception):
    """Le document demande n'existe pas."""

    def __init__(self, document_id: str):
        self.document_id = document_id
        super().__init__(f"Document non trouve: {document_id}")


class InvalidFileTypeError(Exception):
    """Le type de fichier n'est pas supporte."""

    def __init__(self, content_type: str):
        self.content_type = content_type
        super().__init__(
            f"Type de fichier non supporte: {content_type}. Seul PDF est accepte."
        )


class FileTooLargeError(Exception):
    """Le fichier depasse la taille maximale autorisee."""

    def __init__(self, size: int, max_size: int):
        self.size = size
        self.max_size = max_size
        super().__init__(f"Fichier trop volumineux ({size} bytes). Max: {max_size} bytes")


class PageLimitExceededError(Exception):
    """Le nombre de pages PDF depasse la limite autorisee."""

    def __init__(self, current_pages: int, new_pages: int, max_pages: int):
        self.current_pages = current_pages
        self.new_pages = new_pages
        self.max_pages = max_pages
        super().__init__(
            f"Limite de pages depassee: {current_pages} existantes + {new_pages} nouvelles "
            f"= {current_pages + new_pages} pages (max: {max_pages})"
        )
