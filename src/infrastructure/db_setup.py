"""
Script d'initialisation et de verification PostgreSQL pour LangGraph

Ce module fournit des fonctions pour:
1. Tester la connexion a PostgreSQL
2. Creer les tables necessaires (checkpoints, checkpoint_writes, checkpoint_blobs)
3. Verifier que tout est pret pour les agents

Base sur: https://docs.langchain.com/oss/python/langgraph/persistence
"""

import psycopg

from langgraph.checkpoint.postgres import PostgresSaver

from src.config import settings


def _create_companies_table() -> None:
    """
    Cree la table companies pour stocker la configuration des entreprises.

    Cette table permet le multi-tenant: chaque entreprise a son propre
    prompt personnalise (nom, ton).
    """
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS companies (
        company_id VARCHAR(255) PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        tone VARCHAR(255) DEFAULT 'professionnel et courtois',
        plan VARCHAR(50) DEFAULT 'free',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    with psycopg.connect(settings.get_postgres_uri()) as conn:
        with conn.cursor() as cur:
            cur.execute(create_table_sql)
        conn.commit()


def _create_documents_table() -> None:
    """
    Cree la table documents pour stocker les metadonnees des fichiers PDF.
    Multi-tenant via company_id.
    """
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS documents (
        document_id VARCHAR(255) PRIMARY KEY,
        company_id VARCHAR(255) NOT NULL,
        filename VARCHAR(500) NOT NULL,
        gcs_path VARCHAR(1000) NOT NULL,
        size_bytes BIGINT NOT NULL,
        num_pages INTEGER DEFAULT 0,
        content_type VARCHAR(100) DEFAULT 'application/pdf',
        is_vectorized BOOLEAN DEFAULT FALSE,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_documents_company_id
        ON documents(company_id);
    """

    with psycopg.connect(settings.get_postgres_uri()) as conn:
        with conn.cursor() as cur:
            cur.execute(create_table_sql)
        conn.commit()


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

            # Creer la table companies pour le multi-tenant
            print("\nCreation de la table companies (multi-tenant)...")
            _create_companies_table()
            print("Table companies creee avec succes!")

            # Creer la table documents pour les PDF
            print("\nCreation de la table documents (PDF metadata)...")
            _create_documents_table()
            print("Table documents creee avec succes!")

            print("\nTables PostgreSQL creees:")
            print("  - checkpoints: Etats complets du graphe a chaque etape")
            print("  - checkpoint_writes: Ecritures intermediaires (pending writes)")
            print("  - checkpoint_blobs: Stockage de donnees volumineuses")
            print("  - companies: Configuration des entreprises (multi-tenant)")
            print("  - documents: Metadonnees des fichiers PDF (GCS)")

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
