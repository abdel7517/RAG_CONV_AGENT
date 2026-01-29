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
from src.application.simple_agent import SimpleAgent

# Configuration du logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
# Reduire le bruit des logs HTTP (GeneratorExit est normal lors de la fermeture du streaming)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

from src.infrastructure.container import Container
from src.config import settings

container = Container()
container.config.llm_provider.from_value(settings.LLM_PROVIDER)
container.config.channel_type.from_value(settings.CHANNEL_TYPE)
container.wire(modules=["src.application.simple_agent"])


def print_error(message: str):
    """Affiche un message d'erreur formate."""
    print(f"\n[ERREUR] {message}", file=sys.stderr)


def print_success(message: str):
    """Affiche un message de succes formate."""
    print(f"\n[OK] {message}")


def run_simple_agent(thread_id: str):
    """Lance l'agent simple avec gestion des erreurs."""
    try:
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


def run_serve_agent(enable_rag: bool = False):
    """
    Lance l'agent en mode serveur avec gestion des erreurs.

    Le MessageChannel est injecté automatiquement via @inject dans serve().
    Le type de canal (redis/memory) est configuré via container.config.channel_type.
    """
    try:
        agent = SimpleAgent(enable_rag=enable_rag)
        agent_type = "RAG" if enable_rag else "Simple"

        print(f"Demarrage de l'agent {agent_type} en mode serveur...")
        print(f"Type de canal: {settings.CHANNEL_TYPE}")
        if settings.CHANNEL_TYPE == "redis":
            print(f"URL Redis: {settings.REDIS_URL}")

        print(f"\nAgent {agent_type} pret a recevoir des messages sur inbox:*")
        print("(L'initialisation async se fera automatiquement)")
        print("(MessageChannel injecte via @inject)")
        print("Appuyez sur Ctrl+C pour arreter.\n")

        asyncio.run(agent.serve())

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


def run_index_documents(
    documents_path: str = None,
    company_id: str = None,
):
    """
    Indexe les documents PDF dans le vector store.

    Args:
        documents_path: Chemin vers les documents (optionnel, utilise settings.DOCUMENTS_PATH)
        company_id: ID de l'entreprise pour le filtrage multi-tenant
    """
    try:
        path = documents_path or settings.DOCUMENTS_PATH
        print(f"Indexation des documents depuis: {path}")
        print(f"Collection PGVector: {settings.PGVECTOR_COLLECTION_NAME}")
        print(f"Chunk size: {settings.CHUNK_SIZE}, overlap: {settings.CHUNK_OVERLAP}")
        if company_id:
            print(f"Company ID: {company_id}")
        print()

        # Charger et decouper les documents (Factory DI avec param dynamique)
        loader = container.document_loader(documents_path=path)
        chunks = loader.load_and_split(company_id=company_id)

        if not chunks:
            print_error("Aucun document PDF trouve dans le dossier.")
            print(f"Placez vos fichiers PDF dans: {path}")
            sys.exit(1)

        print(f"Documents charges: {len(chunks)} chunks")

        # Indexer dans le vector store (resolu via le container DI)
        async def index():
            vector_store = container.vector_store()
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
        from src.infrastructure.db_setup import setup_postgres
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


def run_add_company(company_id: str, name: str, tone: str):
    """Ajoute ou met a jour une entreprise dans la base de donnees."""
    try:
        from src.infrastructure.repositories.company_repository import CompanyRepository
        from src.domain.models.company import Company

        async def add():
            repo = CompanyRepository()
            company = Company(company_id=company_id, name=name, tone=tone)
            await repo.create(company)

        asyncio.run(add())
        print_success(f"Entreprise '{name}' ({company_id}) ajoutee/mise a jour")
        print(f"  Ton: {tone}")

    except KeyboardInterrupt:
        print("\nArret demande par l'utilisateur.")
        sys.exit(1)
    except ImportError as e:
        print_error(f"Erreur d'import: {e}\nVerifiez que toutes les dependances sont installees: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print_error(f"Erreur lors de l'ajout de l'entreprise: {e}")
        sys.exit(1)


def run_list_companies():
    """Liste toutes les entreprises configurees."""
    try:
        from src.infrastructure.repositories.company_repository import CompanyRepository

        async def list_all():
            repo = CompanyRepository()
            return await repo.list_all()

        companies = asyncio.run(list_all())

        if not companies:
            print("Aucune entreprise configuree.")
            print("\nAjoutez une entreprise avec:")
            print("  python main.py add-company --company-id <ID> --name <NOM> --tone <TON>")
            return

        print(f"\n{'='*60}")
        print(f"{'ENTREPRISES CONFIGUREES':^60}")
        print(f"{'='*60}")
        print(f"{'ID':<20} {'Nom':<25} {'Ton':<15}")
        print(f"{'-'*60}")
        for c in companies:
            print(f"{c.company_id:<20} {c.name:<25} {c.tone:<15}")
        print(f"{'='*60}")
        print(f"Total: {len(companies)} entreprise(s)")

    except Exception as e:
        print_error(f"Erreur lors de la lecture: {e}")
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
  python main.py setup-db                  # Initialiser PostgreSQL

  # Multi-tenant (entreprises)
  python main.py add-company --company-id techstore --name "TechStore" --tone "amical"
  python main.py list-companies            # Lister les entreprises configurees
  python main.py index-documents --company-id techstore  # Indexer les PDFs
        """
    )

    parser.add_argument(
        "command",
        choices=["simple", "rag", "serve", "serve-rag", "index-documents", "setup-db", "add-company", "list-companies"],
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
    parser.add_argument(
        "--name",
        default=None,
        help="Nom de l'entreprise (pour add-company)"
    )
    parser.add_argument(
        "--tone",
        default="professionnel et courtois",
        help="Ton du chatbot (pour add-company, defaut: professionnel et courtois)"
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
        # Reconfigurer le channel si override via CLI
        if args.channel_type:
            container.config.channel_type.from_value(args.channel_type)
        run_serve_agent(enable_rag=False)

    elif args.command == "serve-rag":
        # Reconfigurer le channel si override via CLI
        if args.channel_type:
            container.config.channel_type.from_value(args.channel_type)
        run_serve_agent(enable_rag=True)

    elif args.command == "index-documents":
        if not args.company_id:
            print_error("--company-id est requis pour l'indexation multi-tenant")
            print("Usage: python main.py index-documents --company-id <ID> [--documents-path <PATH>]")
            sys.exit(1)
        run_index_documents(documents_path=args.documents_path, company_id=args.company_id)

    elif args.command == "setup-db":
        run_setup_db()

    elif args.command == "add-company":
        if not args.company_id:
            print_error("--company-id est requis")
            print("Usage: python main.py add-company --company-id <ID> --name <NOM> [--tone <TON>]")
            sys.exit(1)
        if not args.name:
            print_error("--name est requis")
            print("Usage: python main.py add-company --company-id <ID> --name <NOM> [--tone <TON>]")
            sys.exit(1)
        run_add_company(args.company_id, args.name, args.tone)

    elif args.command == "list-companies":
        run_list_companies()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nArret demande par l'utilisateur.")
        sys.exit(0)
    except Exception as e:
        print_error(f"Erreur fatale: {e}")
        sys.exit(1)
