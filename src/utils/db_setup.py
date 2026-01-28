"""
Script d'initialisation et de verification PostgreSQL pour LangGraph

Ce module fournit des fonctions pour:
1. Tester la connexion a PostgreSQL
2. Creer les tables necessaires (checkpoints, checkpoint_writes, checkpoint_blobs)
3. Verifier que tout est pret pour les agents

Base sur: https://docs.langchain.com/oss/python/langgraph/persistence
"""

from langgraph.checkpoint.postgres import PostgresSaver

from src.config import settings


def test_connection() -> bool:
    """
    Teste la connexion a PostgreSQL.

    Returns:
        bool: True si la connexion est reussie, False sinon
    """
    try:
        with PostgresSaver.from_conn_string(settings.get_postgres_uri()):
            return True
    except Exception:
        return False


def setup_postgres() -> bool:
    """
    Initialise PostgreSQL pour LangGraph.

    Returns:
        bool: True si l'initialisation est reussie, False sinon
    """
    print("=" * 70)
    print("INITIALISATION POSTGRESQL POUR LANGGRAPH")
    print("=" * 70)
    print(f"Connection: {settings.get_masked_postgres_uri()}")
    print()

    try:
        print("Test de connexion a PostgreSQL...")
        with PostgresSaver.from_conn_string(settings.get_postgres_uri()) as checkpointer:
            print("Connexion reussie!")

            print("\nCreation des tables LangGraph...")
            checkpointer.setup()
            print("Tables creees avec succes!")

            print("\nTables PostgreSQL creees:")
            print("  - checkpoints: Etats complets du graphe a chaque etape")
            print("  - checkpoint_writes: Ecritures intermediaires (pending writes)")
            print("  - checkpoint_blobs: Stockage de donnees volumineuses")

        print("\n" + "=" * 70)
        print("POSTGRESQL EST PRET!")
        print("=" * 70)
        print("\nVous pouvez maintenant lancer:")
        print("  python main.py simple")
        print("  python main.py rag")
        print()
        print("Les conversations seront sauvegardees dans PostgreSQL")
        print("et persisteront entre les redemarrages!")
        print()
        return True

    except Exception as e:
        print(f"\nERREUR DE CONNEXION: {e}\n")
        print("=" * 70)
        print("TROUBLESHOOTING")
        print("=" * 70)
        print("\nVerifiez que:")
        print("1. PostgreSQL est installe et demarre")
        print("2. La base de donnees 'agent_memory' existe")
        print("3. Les credentials dans .env sont corrects")
        print("4. Le port 5432 n'est pas bloque par un firewall")
        print()
        print("=" * 70)
        print("SOLUTIONS RAPIDES")
        print("=" * 70)
        print()
        print("Option 1: Docker (le plus simple)")
        print("  docker-compose -f docker/docker-compose.yml up -d")
        print()
        print("Option 2: Installation locale")
        print("  macOS:   brew install postgresql@15 && brew services start postgresql@15")
        print("  Ubuntu:  sudo apt-get install postgresql && sudo systemctl start postgresql")
        print()
        print("Option 3: Creer la base de donnees")
        print("  createdb agent_memory")
        print("  # ou: psql -U postgres -c 'CREATE DATABASE agent_memory;'")
        print()
        return False
