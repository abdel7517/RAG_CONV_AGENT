"""
Point d'entree du worker de traitement de documents.

Usage:
    python -m backend.worker
    # ou
    arq backend.worker.settings.WorkerSettings
"""

from arq.worker import run_worker

from backend.worker.settings import WorkerSettings

if __name__ == "__main__":
    run_worker(WorkerSettings)
