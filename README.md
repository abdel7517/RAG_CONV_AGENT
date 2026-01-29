# RAG Conversational Agent

Agent conversationnel intelligent avec **RAG** (Retrieval Augmented Generation), interface web temps reel, et architecture microservices.

## Fonctionnalites

- **Agent LangChain** avec memoire persistante (PostgreSQL)
- **RAG** : recherche semantique dans des documents PDF avec pgvector (PostgreSQL)
- **Multi-tenant** : filtrage des documents par `company_id` pour isoler les donnees par entreprise
- **Multi-LLM** : support Ollama (local), Mistral (API cloud) et OpenAI (API cloud)
- **API REST** avec FastAPI
- **Streaming temps reel** via SSE + Redis Pub/Sub
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

## Stack Technique

| Composant | Technologies |
|-----------|--------------|
| **Agent** | LangChain, LangGraph |
| **RAG** | pgvector (PostgreSQL), pypdf |
| **LLM** | Ollama (local) / Mistral (cloud) / OpenAI (cloud) |
| **Backend** | FastAPI, SSE, Redis Pub/Sub |
| **Frontend** | React, Vite, shadcn/ui |
| **Database** | PostgreSQL (memoire + vectors), Redis (messaging) |
| **Infra** | Docker Compose |

## Structure du projet

```
RAG_CONV_AGENT/
├── src/                          # Agents LangChain
│   ├── agents/
│   │   └── simple_agent.py       # Agent conversationnel (enable_rag option)
│   ├── retrieval/                # Module RAG
│   │   ├── document_loader.py    # Chargement et split des PDFs
│   │   ├── vector_store.py       # pgvector (PostgreSQL)
│   │   └── retriever.py          # Recherche semantique
│   ├── tools/
│   │   └── rag_tools.py          # Tool search_documents pour l'agent
│   ├── messaging/                # Abstraction canaux de messages
│   │   ├── base.py               # Interface MessageChannel
│   │   ├── redis_channel.py      # Implementation Redis
│   │   ├── memory_channel.py     # Implementation In-Memory
│   │   └── factory.py            # Factory create_channel()
│   ├── config/
│   │   └── settings.py           # Configuration centralisee
│   └── utils/
│       └── db_setup.py           # Setup PostgreSQL
│
├── backend/                      # API FastAPI
│   ├── main.py                   # Application FastAPI
│   ├── dependencies.py           # Broadcaster Redis
│   └── routes/
│       ├── chat.py               # POST /chat
│       └── stream.py             # GET /stream/{email} (SSE)
│
├── frontend/                     # Interface React
│   ├── src/
│   │   ├── App.jsx               # Composant principal
│   │   ├── components/           # Composants UI (ChatWidget, etc.)
│   │   └── hooks/                # Custom hooks (SSE)
│   └── package.json
│
├── documents/                    # Documents PDF pour RAG
├── docker-compose.yml            # PostgreSQL + Redis
├── main.py                       # CLI agents
└── requirements.txt
```

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

**Option A: Ollama (local, gratuit)**
```bash
# Installer depuis https://ollama.ai
ollama pull phi3:mini
ollama pull nomic-embed-text
ollama serve
```

**Option B: Mistral (cloud)**
```bash
# Dans .env
LLM_PROVIDER=mistral
MISTRAL_API_KEY=votre_cle_api
```

### 4. Initialiser la base de donnees

```bash
python main.py setup-db
```

### 5. (Optionnel) Indexer des documents pour le RAG

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
| `/health` | GET | Health check |

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
# LLM Provider
LLM_PROVIDER=ollama              # ou "mistral"

# Ollama
OLLAMA_MODEL=phi3:mini
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Mistral (si LLM_PROVIDER=mistral)
MISTRAL_API_KEY=votre_cle
MISTRAL_MODEL=mistral-small-latest

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
