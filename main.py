#!/usr/bin/env python3
"""
RAG Conversational Agent - Point d'entree principal

Ce script fournit une interface CLI unifiee pour lancer les differents
agents du projet.

Usage:
    python main.py simple [--thread-id ID]     Lance l'agent simple
    python main.py rag [--thread-id ID]        Lance l'agent RAG
    python main.py serve [--channel-type TYPE] Lance l'agent en mode serveur
    python main.py serve-rag [--channel-type TYPE] Lance l'agent RAG en mode serveur
    python main.py index-documents             Indexe les documents PDF
    python main.py setup-db                    Configure PostgreSQL
"""

import argparse
import asyncio
import logging
import sys

# Configuration du logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
# Reduire le bruit des logs HTTP (GeneratorExit est normal lors de la fermeture du streaming)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


def print_error(message: str):
    """Affiche un message d'erreur formate."""
    print(f"\n[ERREUR] {message}", file=sys.stderr)


def print_success(message: str):
    """Affiche un message de succes formate."""
    print(f"\n[OK] {message}")


def run_simple_agent(thread_id: str):
    """Lance l'agent simple avec gestion des erreurs."""
    try:
        from src.agents import SimpleAgent
        agent = SimpleAgent()

        async def run():
            await agent.initialize()
            print(f"Agent simple initialise (thread: {thread_id})")
            print("Tapez votre message (Ctrl+C pour quitter):\n")

            try:
                while True:
                    user_input = input("Vous: ")
                    if not user_input.strip():
                        continue

                    print("Assistant: ", end="", flush=True)
                    async for chunk in agent.chat(user_input, thread_id=thread_id):
                        print(chunk, end="", flush=True)
                    print("\n")
            finally:
                await agent.cleanup()

        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nArret demande par l'utilisateur.")
    except ImportError as e:
        print_error(f"Erreur d'import: {e}\nVerifiez que toutes les dependances sont installees: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print_error(f"Erreur inattendue: {e}")
        sys.exit(1)


def run_rag_agent(thread_id: str):
    """Lance l'agent RAG avec gestion des erreurs."""
    try:
        from src.agents import SimpleAgent
        agent = SimpleAgent(enable_rag=True)

        async def run():
            await agent.initialize()
            print(f"Agent RAG initialise (thread: {thread_id})")
            print("L'agent peut rechercher dans vos documents PDF.")
            print("Tapez votre message (Ctrl+C pour quitter):\n")

            try:
                while True:
                    user_input = input("Vous: ")
                    if not user_input.strip():
                        continue

                    print("Assistant: ", end="", flush=True)
                    async for chunk in agent.chat(user_input, thread_id=thread_id):
                        print(chunk, end="", flush=True)
                    print("\n")
            finally:
                await agent.cleanup()

        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nArret demande par l'utilisateur.")
    except ImportError as e:
        print_error(f"Erreur d'import: {e}\nVerifiez que toutes les dependances sont installees: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print_error(f"Erreur inattendue: {e}")
        sys.exit(1)


def run_serve_agent(channel_type: str, redis_url: str, enable_rag: bool = False):
    """Lance l'agent en mode serveur avec gestion des erreurs."""
    try:
        from src.messaging import create_channel
        from src.agents import SimpleAgent

        agent = SimpleAgent(enable_rag=enable_rag)
        agent_type = "RAG" if enable_rag else "Simple"

        print(f"Demarrage de l'agent {agent_type} en mode serveur...")
        print(f"Type de canal: {channel_type}")
        if channel_type == "redis":
            print(f"URL Redis: {redis_url}")

        channel = create_channel(channel_type, url=redis_url)
        print(f"Canal {channel_type} configure.")

        print(f"\nAgent {agent_type} pret a recevoir des messages sur inbox:*")
        print("(L'initialisation async se fera automatiquement)")
        print("Appuyez sur Ctrl+C pour arreter.\n")

        asyncio.run(agent.serve(channel))

    except KeyboardInterrupt:
        print("\nArret demande par l'utilisateur.")
    except ImportError as e:
        print_error(f"Erreur d'import: {e}\nVerifiez que toutes les dependances sont installees: pip install -r requirements.txt")
        sys.exit(1)
    except ConnectionError as e:
        print_error(f"Erreur de connexion: {e}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Erreur inattendue: {e}")
        sys.exit(1)


def run_index_documents(documents_path: str = None, company_id: str = None):
    """
    Indexe les documents PDF dans le vector store.

    Args:
        documents_path: Chemin vers les documents (optionnel, utilise settings.DOCUMENTS_PATH)
        company_id: ID de l'entreprise pour le filtrage multi-tenant
    """
    try:
        from src.retrieval import DocumentLoader, VectorStore
        from src.config import settings

        path = documents_path or settings.DOCUMENTS_PATH
        print(f"Indexation des documents depuis: {path}")
        print(f"Collection PGVector: {settings.PGVECTOR_COLLECTION_NAME}")
        print(f"Chunk size: {settings.CHUNK_SIZE}, overlap: {settings.CHUNK_OVERLAP}")
        if company_id:
            print(f"Company ID: {company_id}")
        print()

        # Charger et decouper les documents
        loader = DocumentLoader(documents_path=path)
        chunks = loader.load_and_split(company_id=company_id)

        if not chunks:
            print_error("Aucun document PDF trouve dans le dossier.")
            print(f"Placez vos fichiers PDF dans: {path}")
            sys.exit(1)

        print(f"Documents charges: {len(chunks)} chunks")

        # Indexer dans le vector store
        vector_store = VectorStore()

        async def index():
            await vector_store.create_from_documents(chunks)

        asyncio.run(index())

        print_success(f"Indexation terminee: {len(chunks)} chunks dans '{settings.PGVECTOR_COLLECTION_NAME}'")

    except KeyboardInterrupt:
        print("\nArret demande par l'utilisateur.")
        sys.exit(1)
    except ImportError as e:
        print_error(f"Erreur d'import: {e}\nVerifiez que toutes les dependances sont installees: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print_error(f"Erreur lors de l'indexation: {e}")
        sys.exit(1)


def run_setup_db():
    """Configure PostgreSQL avec gestion des erreurs."""
    try:
        from src.utils import setup_postgres
        success = setup_postgres()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nArret demande par l'utilisateur.")
        sys.exit(1)
    except ImportError as e:
        print_error(f"Erreur d'import: {e}\nVerifiez que toutes les dependances sont installees: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print_error(f"Erreur inattendue: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="RAG Conversational Agent - CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python main.py simple                    # Lancer l'agent simple
  python main.py rag --thread-id user123   # Lancer l'agent RAG avec un thread specifique
  python main.py serve                     # Lancer l'agent simple en mode serveur (Redis)
  python main.py serve-rag                 # Lancer l'agent RAG en mode serveur
  python main.py index-documents --company-id techstore_123  # Indexer les PDFs
  python main.py index-documents --company-id acme_456 --documents-path ./docs/acme
  python main.py setup-db                  # Initialiser PostgreSQL
        """
    )

    parser.add_argument(
        "command",
        choices=["simple", "rag", "serve", "serve-rag", "index-documents", "setup-db"],
        help="Commande a executer"
    )
    parser.add_argument(
        "--thread-id",
        default=None,
        help="Identifiant de la conversation (pour simple et rag)"
    )
    parser.add_argument(
        "--channel-type",
        default=None,
        choices=["redis", "memory"],
        help="Type de canal pour le mode serve (defaut: redis)"
    )
    parser.add_argument(
        "--redis-url",
        default=None,
        help="URL Redis pour le mode serve (defaut: redis://localhost:6379)"
    )
    parser.add_argument(
        "--company-id",
        default=None,
        help="ID de l'entreprise pour le filtrage multi-tenant (pour index-documents)"
    )
    parser.add_argument(
        "--documents-path",
        default=None,
        help="Chemin vers les documents a indexer (pour index-documents)"
    )

    # Gerer le cas ou aucun argument n'est fourni
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    if args.command == "simple":
        thread_id = args.thread_id or "user-session-1"
        run_simple_agent(thread_id)

    elif args.command == "rag":
        thread_id = args.thread_id or "user-rag-session-1"
        run_rag_agent(thread_id)

    elif args.command == "serve":
        from src.config import settings
        channel_type = args.channel_type or settings.CHANNEL_TYPE
        redis_url = args.redis_url or settings.REDIS_URL
        run_serve_agent(channel_type, redis_url, enable_rag=False)

    elif args.command == "serve-rag":
        from src.config import settings
        channel_type = args.channel_type or settings.CHANNEL_TYPE
        redis_url = args.redis_url or settings.REDIS_URL
        run_serve_agent(channel_type, redis_url, enable_rag=True)

    elif args.command == "index-documents":
        if not args.company_id:
            print_error("--company-id est requis pour l'indexation multi-tenant")
            print("Usage: python main.py index-documents --company-id <ID> [--documents-path <PATH>]")
            sys.exit(1)
        run_index_documents(documents_path=args.documents_path, company_id=args.company_id)

    elif args.command == "setup-db":
        run_setup_db()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nArret demande par l'utilisateur.")
        sys.exit(0)
    except Exception as e:
        print_error(f"Erreur fatale: {e}")
        sys.exit(1)
