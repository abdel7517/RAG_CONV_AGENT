# RAG Conversational Agent Multi-tenant

Agent conversationnel intelligent avec **RAG** (Retrieval Augmented Generation), interface web temps reel, et architecture microservices.

## Fonctionnalites

- **Agent LangChain** avec memoire persistante (PostgreSQL)
- **RAG** : recherche semantique dans des documents PDF avec pgvector (PostgreSQL)
- **Multi-tenant** : filtrage des documents par `company_id` pour isoler les donnees par entreprise
- **Multi-LLM** : support Ollama (local), Mistral (API cloud) et OpenAI (API cloud)
- **API REST** avec FastAPI
- **Streaming temps reel** via SSE + Redis Pub/Sub
- **Upload de documents PDF** via Google Cloud Storage avec gestion CRUD depuis le frontend
- **Interface web React** avec chat en temps reel

## Architecture

```
┌──────────────┐     POST /chat     ┌──────────────┐
│   Frontend   │ ─────────────────▶ │   FastAPI    │
│   (React)    │                    │   Backend    │
└──────────────┘                    └──────────────┘
       ▲                                   │
       │                                   │ PUBLISH
       │ SSE                               ▼
       │ (streaming)              ┌──────────────┐
       │                          │    Redis     │
       │                          │   Pub/Sub    │
       │                          └──────────────┘
       │                                   │
       │                                   │ SUBSCRIBE
       │         PUBLISH                   ▼
       └─────────────────────────  ┌──────────────┐
                                   │    Agent     │
                                   │   Worker     │
                                   │  (LangChain) │
                                   └──────────────┘
```

### Flow detaille

```
Frontend                    Backend (FastAPI)              Redis             Worker (LangChain)
   │                              │                          │                  │
   ├── POST /api/chat ──────────► │                          │                  │
   │   {email, message}           ├── broker.publish() ────► │                  │
   │                              │   inbox:email            │                  │
   │   ◄── {status: "queued"} ────┤                          │                  │
   │                              │                          ├── inbox:email ──►│
   │                              │                          │                  │ RAG + LLM
   ├── GET /stream/email ────────►│                          │                  │
   │   (SSE connexion ouverte)    ├── broker.subscribe() ──► │                  │
   │                              │   outbox:email           │  ◄── chunk 1 ────┤
   │   ◄── chunk 1 ───────────────┤ ◄────────────────────────┤                  │
   │   ◄── chunk 2 ───────────────┤ ◄────────────────────────┤  ◄── chunk 2 ────┤
   │   ◄── {done: true} ──────────┤ ◄────────────────────────┤  ◄── done ───────┤
   │   (connexion fermee)         │                          │                  │
```

> Le backend est un **passe-plat** : il ne fait aucune IA. Il recoit du frontend, publie dans Redis, et retransmet les reponses du worker vers le frontend via SSE.

## Stack Technique

| Composant | Technologies |
|-----------|--------------|
| **Agent** | LangChain, LangGraph |
| **RAG** | pgvector (PostgreSQL), pypdf |
| **LLM** | Ollama (local) / Mistral (cloud) / OpenAI (cloud) |
| **Embeddings** | HuggingFace (local) / Ollama (local) / Mistral (cloud) / OpenAI (cloud) |
| **Backend** | FastAPI, SSE, Redis Pub/Sub |
| **Frontend** | React, Vite, shadcn/ui, React Router |
| **Stockage fichiers** | Google Cloud Storage (PDF upload) |
| **Database** | PostgreSQL (memoire + vectors + metadata docs), Redis (messaging) |
| **Infra** | Docker Compose |

## Structure du projet (Clean Architecture)

```
RAG_CONV_AGENT/
├── src/
│   ├── domain/                          # Couche Domain (entites + ports)
│   │   ├── models/
│   │   │   └── company.py               # Modele Company (multi-tenant)
│   │   └── ports/
│   │       ├── vector_store_port.py     # Interface VectorStore
│   │       ├── retriever_port.py        # Interface Retriever
│   │       ├── document_loader_port.py  # Interface DocumentLoader
│   │       ├── message_channel_port.py  # Interface MessageChannel + Message
│   │       └── llm_port.py             # Interface LLM
│   │
│   ├── application/                     # Couche Application (orchestration)
│   │   ├── simple_agent.py              # Agent conversationnel (enable_rag option)
│   │   ├── rag_tools.py                 # Tool search_documents + RAGAgentState
│   │   └── services/
│   │       ├── rag_service.py           # Service RAG (recherche + formatage)
│   │       └── messaging_service.py     # Service messaging (publish/listen)
│   │
│   ├── infrastructure/                  # Couche Infrastructure (implementations)
│   │   ├── adapters/
│   │   │   ├── pgvector_adapter.py      # PGVector (VectorStorePort + RetrieverPort)
│   │   │   ├── document_loader_adapter.py # PDF loader (DocumentLoaderPort)
│   │   │   ├── redis_channel_adapter.py   # Redis Pub/Sub (MessageChannel)
│   │   │   ├── memory_channel_adapter.py  # In-Memory (MessageChannel)
│   │   │   ├── ollama_adapter.py        # Ollama LLM (LLMPort)
│   │   │   ├── mistral_adapter.py       # Mistral LLM (LLMPort)
│   │   │   └── openai_adapter.py        # OpenAI LLM (LLMPort)
│   │   ├── repositories/
│   │   │   └── company_repository.py    # Repository Company (PostgreSQL)
│   │   ├── container.py                 # Container DI (dependency-injector)
│   │   └── db_setup.py                  # Setup PostgreSQL
│   │
│   └── config/
│       └── settings.py                  # Configuration centralisee
│
├── backend/                             # API FastAPI (Hexagonal)
│   ├── main.py                          # Application FastAPI + Container DI
│   ├── domain/
│   │   ├── models/
│   │   │   ├── chat.py                  # ChatRequest, ChatResponse
│   │   │   └── document.py             # Document, DocumentResponse, etc.
│   │   └── ports/
│   │       ├── event_broker_port.py     # Interface EventBroker (pub/sub)
│   │       ├── file_storage_port.py     # Interface FileStorage (GCS)
│   │       └── document_repository_port.py # Interface DocumentRepository
│   ├── infrastructure/
│   │   ├── container.py                 # Container DI (dependency-injector)
│   │   ├── adapters/
│   │   │   ├── broadcast_adapter.py     # Redis Broadcast (EventBrokerPort)
│   │   │   └── gcs_storage_adapter.py   # Google Cloud Storage (FileStoragePort)
│   │   └── repositories/
│   │       └── document_repository.py   # PostgreSQL (DocumentRepositoryPort)
│   └── routes/
│       ├── chat.py                      # POST /chat (@inject)
│       ├── stream.py                    # GET /stream/{email} SSE (@inject)
│       └── documents.py                 # CRUD /documents (@inject)
│
├── frontend/                            # Interface React
│   ├── src/
│   │   ├── App.jsx                      # Composant principal + routing
│   │   ├── components/
│   │   │   ├── ChatWidget.jsx           # Widget chat SSE
│   │   │   ├── DocumentsPage.jsx        # Page gestion documents (CRUD)
│   │   │   └── DemoEcommerceWebsite.jsx # Page demo e-commerce
│   │   └── hooks/                       # Custom hooks (SSE)
│   └── package.json
│
├── documents/                           # Documents PDF pour RAG
├── docker-compose.yml                   # PostgreSQL + Redis
├── main.py                              # CLI agents
└── requirements.txt
```

### Principes architecturaux

- **Ports & Adapters (Hexagonal)** : Les ports (`domain/ports/`) definissent les interfaces. Les adapters (`infrastructure/adapters/`) les implementent.
- **Dependency Injection** : Le container DI (`dependency-injector`) gere le wiring. Les services dependent des ports, pas des implementations.
- **Inversion de dependance** : La couche application ne connait que les abstractions. Changer de provider (ex: PGVector → Pinecone) = changer un adapter sans toucher aux services.

## Quick Start

### 1. Lancer les services (PostgreSQL + Redis)

```bash
docker-compose up -d
```

### 2. Installer les dependances Python

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configurer le LLM

**Option A: 100% local (gratuit, donnees non partagees a des tiers)**

Recommande pour ceux qui souhaitent conserver leurs donnees en local. Aucune information n'est envoyee a un service externe.

> **Configuration minimale requise** : 16 Go de RAM, 10 Go d'espace disque libre. Un GPU est recommande mais pas obligatoire (le CPU fonctionne, mais plus lentement).

```bash
# Installer Ollama depuis https://ollama.ai
ollama pull qwen2.5:7b
ollama serve

# Dans .env
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen2.5:7b
EMBEDDING_PROVIDER=huggingface
HUGGINGFACE_EMBEDDING_MODEL=intfloat/multilingual-e5-large
```

> Les embeddings HuggingFace sont telecharges localement via `sentence-transformers`. Le modele LLM tourne via Ollama. Aucune donnee n'est envoyee a un service externe.

**Option B: Mistral (cloud)**

Pour ceux qui n'ont pas la configuration materielle necessaire pour l'option locale. Les requetes sont envoyees aux serveurs Mistral.

```bash
# Dans .env
LLM_PROVIDER=mistral
MISTRAL_API_KEY=votre_cle_api

# Optionnel: garder les embeddings en local (pas de partage de donnees pour l'indexation)
EMBEDDING_PROVIDER=huggingface
HUGGINGFACE_EMBEDDING_MODEL=intfloat/multilingual-e5-large

# Ou utiliser les embeddings Mistral (cloud)
# EMBEDDING_PROVIDER=mistral
```

**Option C: OpenAI (cloud)**

Pour ceux qui n'ont pas la configuration materielle necessaire pour l'option locale. Les requetes sont envoyees aux serveurs OpenAI.

```bash
# Dans .env
LLM_PROVIDER=openai
OPENAI_API_KEY=votre_cle_api

# Optionnel: garder les embeddings en local (pas de partage de donnees pour l'indexation)
EMBEDDING_PROVIDER=huggingface
HUGGINGFACE_EMBEDDING_MODEL=intfloat/multilingual-e5-large

# Ou utiliser les embeddings OpenAI (cloud)
# EMBEDDING_PROVIDER=openai
```

### 4. Initialiser la base de donnees

```bash
python main.py setup-db
```

### 5. Indexer des documents pour le RAG

Placez vos fichiers PDF dans le dossier `documents/` puis indexez-les avec un `company_id` :

```bash
# Indexer les documents pour une entreprise specifique
python main.py index-documents --company-id techstore_123

# Indexer depuis un dossier personnalise
python main.py index-documents --company-id acme_456 --documents-path ./docs/acme
```

> **Note Multi-tenant** : Le `company_id` permet d'isoler les documents par entreprise. Chaque requete de chat doit inclure le meme `company_id` pour acceder aux bons documents.

### 6. Lancer l'application

```bash
# Terminal 1: API FastAPI
uvicorn backend.main:app --reload --port 8000

# Terminal 2: Agent en mode serveur
python main.py serve-rag

# Terminal 3: Frontend React
cd frontend && npm install && npm run dev
```

Ouvrir http://localhost:3000

## Utilisation CLI

```bash
# Agent simple (conversation interactive)
python main.py simple

# Agent avec RAG (recherche dans les documents PDF)
python main.py rag

# Agent en mode serveur (ecoute Redis)
python main.py serve

# Agent RAG en mode serveur
python main.py serve-rag

# Mode serveur avec canal In-Memory (tests)
python main.py serve --channel-type memory

# Indexer les documents PDF dans pgvector (multi-tenant)
python main.py index-documents --company-id <ID>
python main.py index-documents --company-id techstore_123 --documents-path ./docs/techstore

# Initialiser PostgreSQL
python main.py setup-db

# Avec Mistral
LLM_PROVIDER=mistral python main.py simple
```

## API Endpoints

| Endpoint | Methode | Description |
|----------|---------|-------------|
| `/api/chat` | POST | Envoyer un message |
| `/api/stream/{email}` | GET | SSE streaming reponse |
| `/api/documents/upload` | POST | Upload un document PDF (multipart) |
| `/api/documents` | GET | Lister les documents d'une entreprise |
| `/api/documents/{id}` | DELETE | Supprimer un document (GCS + DB) |
| `/health` | GET | Health check |

### Exemple POST /documents/upload

```bash
curl -X POST "http://localhost:8000/api/documents/upload?company_id=techstore_123" \
  -F "file=@mon_document.pdf"
```

### Exemple GET /documents

```bash
curl "http://localhost:8000/api/documents?company_id=techstore_123"
```

### Exemple POST /chat

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": "techstore_123",
    "email": "user@example.com",
    "message": "Quels sont vos delais de livraison?"
  }'
```

> **Note** : Le `company_id` est obligatoire et permet de filtrer les documents RAG par entreprise.

## Configuration

Variables d'environnement (`.env`):

```bash
# LLM Provider ("ollama", "mistral" ou "openai")
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_BASE_URL=http://localhost:11434

# Embedding Provider (optionnel, defaut = LLM_PROVIDER)
# Permet d'utiliser un provider d'embedding different du LLM
# Valeurs: ollama, mistral, openai, huggingface
EMBEDDING_PROVIDER=huggingface
HUGGINGFACE_EMBEDDING_MODEL=intfloat/multilingual-e5-large

# Mistral (si LLM_PROVIDER=mistral)
MISTRAL_API_KEY=votre_cle
MISTRAL_MODEL=mistral-small-latest

# OpenAI (si LLM_PROVIDER=openai)
OPENAI_API_KEY=votre_cle
OPENAI_MODEL=gpt-4o-mini

# Redis
REDIS_URL=redis://localhost:6379

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=agent_memory
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# RAG / pgvector
PGVECTOR_COLLECTION_NAME=documents
DOCUMENTS_PATH=./documents
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Google Cloud Storage (upload de documents PDF)
GCS_BUCKET_NAME=votre-bucket-name
GCS_PROJECT_ID=votre-project-id
GCS_SERVICE_ACCOUNT_KEY={"type":"service_account","project_id":"...","private_key":"...","client_email":"..."}
# MAX_UPLOAD_SIZE_BYTES=10485760
```

## Concepts Cles

### RAG Direct (Retrieval Augmented Generation)

L'agent utilise pgvector (extension PostgreSQL) pour le stockage vectoriel avec une approche **RAG Direct** :
la recherche en base est effectuee **systematiquement avant chaque appel LLM**, et le contexte est injecte dans le message.

1. **Indexation** : PDFs → Chunks → Embeddings → pgvector (avec `company_id`)
2. **Query** : Question → Recherche semantique (filtree par `company_id`) → Contexte injecte dans le message → LLM → Reponse

```
User: "Quels sont vos delais ?"
  │
  ▼
chat() → rag_service.search_formatted(query, company_id)
  │
  ├─ Aucun document → "Je n'ai pas cette information." (pas d'appel LLM)
  │
  └─ Documents trouves → Message enrichi:
       "CONTEXTE DOCUMENTAIRE:\n{contexte}\n\n---\nQUESTION: {question}"
         │
         ▼
       LLM repond en se basant uniquement sur le contexte
```

```python
# Agent sans RAG
agent = SimpleAgent()

# Agent avec RAG active (recherche systematique avant LLM)
agent = SimpleAgent(enable_rag=True)
```

### Multi-tenant (Filtrage par company_id)

Le systeme supporte l'isolation des donnees par entreprise :

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend envoie: { company_id, email, message }            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Agent extrait company_id et filtre les documents RAG       │
│  → Seuls les documents avec metadata.company_id = X         │
│    sont retournes par la recherche semantique               │
└─────────────────────────────────────────────────────────────┘
```

**Indexation** :
```bash
# Documents de l'entreprise A
python main.py index-documents --company-id entreprise_A --documents-path ./docs/A

# Documents de l'entreprise B
python main.py index-documents --company-id entreprise_B --documents-path ./docs/B
```

**Frontend** :
```jsx
<ChatWidget companyId="entreprise_A" />
```

**Isolation garantie** : Les requetes de `entreprise_A` ne voient jamais les documents de `entreprise_B`.

### Gestion des Documents (Upload PDF)

Les documents PDF peuvent etre uploades depuis le frontend et stockes dans Google Cloud Storage.
Les metadonnees (nom, taille, date) sont enregistrees dans PostgreSQL.

```
Frontend (/documents)          Backend (FastAPI)            GCS + PostgreSQL
   │                                 │                          │
   ├── POST /documents/upload ─────► │                          │
   │   (multipart + company_id)      ├── upload fichier ──────► │ GCS: bucket/{company_id}/{id}.pdf
   │                                 ├── save metadata ───────► │ PostgreSQL: table documents
   │   ◄── {status: "uploaded"} ─────┤                          │
   │                                 │                          │
   ├── GET /documents ──────────────►│                          │
   │   (company_id)                  ├── SELECT * ────────────► │ PostgreSQL
   │   ◄── [liste documents] ───────┤                          │
   │                                 │                          │
   ├── DELETE /documents/{id} ──────►│                          │
   │   (company_id)                  ├── delete blob ─────────► │ GCS
   │                                 ├── DELETE row ──────────► │ PostgreSQL
   │   ◄── {status: "deleted"} ─────┤                          │
```

**Frontend** : Accessible via `http://localhost:3000/documents`

**Isolation multi-tenant** : Chaque requete necessite un `company_id`. Les documents d'une entreprise ne sont jamais visibles par une autre.

### Architecture Event-Driven

- **Redis Pub/Sub** pour la communication asynchrone
- **SSE** pour le streaming temps reel vers le frontend
- **Worker** decouple pour le traitement des messages

### Memoire Persistante

- **PostgreSQL** via LangGraph checkpointer
- Historique par `thread_id` (email utilisateur)
- Reprise de conversation entre sessions

## Licence

MIT
