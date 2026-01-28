# RAG Tool Flow - Workflow Complet

## Vue d'ensemble

Ce document explique le flux complet du systeme RAG multi-tenant, de la requete utilisateur jusqu'a la reponse finale.

---

## 1. Flux Global (Sans Code)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FLUX COMPLET RAG MULTI-TENANT                        │
└─────────────────────────────────────────────────────────────────────────────┘

    UTILISATEUR                                              BASE DE DONNEES
         │                                                         │
         │  "Quels sont vos delais de livraison ?"                │
         │  + company_id: "techstore"                              │
         │  + email: "client@example.com"                          │
         ▼                                                         │
┌─────────────────┐                                                │
│    FRONTEND     │                                                │
│   (React App)   │                                                │
└────────┬────────┘                                                │
         │                                                         │
         │  POST /api/chat                                         │
         │  { company_id, email, message }                         │
         ▼                                                         │
┌─────────────────┐                                                │
│    BACKEND      │                                                │
│   (FastAPI)     │                                                │
└────────┬────────┘                                                │
         │                                                         │
         │  PUBLISH vers Redis                                     │
         │  Canal: inbox:{email}                                   │
         ▼                                                         │
┌─────────────────┐                                                │
│     REDIS       │                                                │
│    Pub/Sub      │                                                │
└────────┬────────┘                                                │
         │                                                         │
         │  SUBSCRIBE inbox:*                                      │
         ▼                                                         │
┌─────────────────┐      Recupere config entreprise      ┌─────────────────┐
│     AGENT       │ ────────────────────────────────────▶│   POSTGRESQL    │
│   (LangChain)   │◀──────────────────────────────────── │   (companies)   │
└────────┬────────┘   { name: "TechStore", tone: "amical" }        │
         │                                                         │
         │  Cree/utilise un agent avec                             │
         │  le prompt personnalise                                 │
         ▼                                                         │
┌─────────────────┐                                                │
│      LLM        │                                                │
│ (Mistral/Ollama)│                                                │
└────────┬────────┘                                                │
         │                                                         │
         │  Le LLM analyse la question                             │
         │  et decide d'appeler le tool                            │
         ▼                                                         │
┌─────────────────┐      Recherche vectorielle           ┌─────────────────┐
│ search_documents│ ────────────────────────────────────▶│   POSTGRESQL    │
│     (Tool)      │◀──────────────────────────────────── │   (pgvector)    │
└────────┬────────┘   Documents filtres par company_id   └─────────────────┘
         │
         │  Contexte: "[Document 1] Delais: 2-5 jours..."
         ▼
┌─────────────────┐
│      LLM        │
│  (Generation)   │
└────────┬────────┘
         │
         │  Genere la reponse finale
         │  en utilisant le contexte
         ▼
┌─────────────────┐
│     AGENT       │
│   (Streaming)   │
└────────┬────────┘
         │
         │  PUBLISH vers Redis
         │  Canal: outbox:{email}
         │  { chunk: "D'apres...", done: false }
         ▼
┌─────────────────┐
│     REDIS       │
└────────┬────────┘
         │
         │  SSE Stream
         ▼
┌─────────────────┐
│    FRONTEND     │
│  (Affichage)    │
└────────┬────────┘
         │
         ▼
    UTILISATEUR

    "D'apres notre documentation, les delais de livraison
     sont de 2-5 jours ouvres. [Source: CGV]"
```

---

## 2. Etapes Detaillees

### Etape 1 : Requete Utilisateur

L'utilisateur envoie un message via l'interface de chat. La requete contient :
- **company_id** : Identifiant de l'entreprise (ex: "techstore")
- **email** : Identifiant de session (ex: "client@example.com")
- **message** : La question posee

### Etape 2 : Routage Backend

Le backend FastAPI recoit la requete et la publie sur Redis dans un canal specifique a l'utilisateur (`inbox:{email}`). Cela permet un traitement asynchrone.

### Etape 3 : Reception par l'Agent

L'agent ecoute tous les canaux `inbox:*` et recoit le message. Il extrait le `company_id` pour configurer le contexte.

### Etape 4 : Configuration Multi-tenant

L'agent interroge PostgreSQL pour recuperer les informations de l'entreprise :
- **Nom** : "TechStore"
- **Ton** : "amical et decontracte"

Ces informations servent a personnaliser le prompt systeme.

### Etape 5 : Analyse par le LLM

Le LLM recoit la question avec un prompt personnalise :
> "Tu es un chatbot de **TechStore**... Ton: **amical**..."

Le LLM analyse la question et decide s'il doit rechercher des informations.

### Etape 6 : Appel du Tool (Decision du LLM)

Si la question necessite des informations factuelles, le LLM appelle automatiquement le tool `search_documents` avec une requete de recherche.

**Exemples de questions declenchant le tool :**
- "Quels sont vos delais de livraison ?"
- "Quelle est votre politique de retour ?"
- "Combien coute le produit X ?"

**Exemples de questions NE declenchant PAS le tool :**
- "Bonjour !"
- "Merci pour l'info"
- "Peux-tu reformuler ?"

### Etape 7 : Recherche Vectorielle

Le tool effectue une recherche semantique dans pgvector :
1. La question est convertie en vecteur (embedding)
2. Les documents les plus similaires sont recuperes
3. **Filtre multi-tenant** : Seuls les documents avec `company_id = "techstore"` sont retournes

### Etape 8 : Formatage du Contexte

Les documents trouves sont formates en texte lisible :
```
[Document 1]
Source: CGV.pdf (page 2)
Contenu: Delais de livraison : 2-5 jours ouvres pour la France...

---

[Document 2]
Source: FAQ.pdf (page 1)
Contenu: Livraison express disponible en 24h moyennant 9.99EUR...
```

### Etape 9 : Generation de la Reponse

Le LLM recoit le contexte et genere une reponse naturelle en citant les sources :
> "D'apres notre documentation, les delais de livraison sont de 2-5 jours ouvres pour la France metropolitaine. Une option express en 24h est disponible pour 9.99EUR. [Source: CGV, FAQ]"

### Etape 10 : Streaming vers l'Utilisateur

La reponse est streamee token par token via Redis et SSE, permettant un affichage progressif dans l'interface.

---

## 3. Isolation Multi-tenant

```
┌─────────────────────────────────────────────────────────────────┐
│                    ISOLATION DES DONNEES                        │
└─────────────────────────────────────────────────────────────────┘

  Entreprise A (techstore)          Entreprise B (acme)
         │                                 │
         ▼                                 ▼
┌─────────────────┐              ┌─────────────────┐
│  Documents A    │              │  Documents B    │
│  - CGV_A.pdf    │              │  - CGV_B.pdf    │
│  - FAQ_A.pdf    │              │  - FAQ_B.pdf    │
│  - Produits_A   │              │  - Produits_B   │
└────────┬────────┘              └────────┬────────┘
         │                                 │
         │ company_id = "techstore"        │ company_id = "acme"
         ▼                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                         PGVECTOR                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ id │ content          │ embedding │ company_id         │   │
│  ├────┼──────────────────┼───────────┼────────────────────┤   │
│  │ 1  │ "Delais: 2-5j"   │ [0.1,...] │ techstore          │   │
│  │ 2  │ "Delais: 3-7j"   │ [0.2,...] │ acme               │   │
│  │ 3  │ "Retour: 30j"    │ [0.3,...] │ techstore          │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘

Requete company_id="techstore" → Ne voit QUE les documents 1 et 3
Requete company_id="acme"      → Ne voit QUE le document 2
```

**Garantie** : Une entreprise ne peut JAMAIS acceder aux documents d'une autre entreprise.

---

## 4. Personnalisation du Prompt

```
┌─────────────────────────────────────────────────────────────────┐
│                  PROMPT PERSONNALISE PAR ENTREPRISE             │
└─────────────────────────────────────────────────────────────────┘

                    Table "companies"
┌──────────────┬─────────────┬──────────────────────────┐
│ company_id   │ name        │ tone                     │
├──────────────┼─────────────┼──────────────────────────┤
│ techstore    │ TechStore   │ amical et decontracte    │
│ acme         │ Acme Corp   │ professionnel et formel  │
│ boutique     │ La Boutique │ chaleureux et proche     │
└──────────────┴─────────────┴──────────────────────────┘
                              │
                              ▼
                    Template de Prompt
         "Tu es un chatbot de {name}...
          Ton: {tone}..."
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Agent TechStore │  │  Agent Acme     │  │ Agent Boutique  │
│                 │  │                 │  │                 │
│ Prompt:         │  │ Prompt:         │  │ Prompt:         │
│ "Tu es un       │  │ "Tu es un       │  │ "Tu es un       │
│  chatbot de     │  │  chatbot de     │  │  chatbot de     │
│  TechStore...   │  │  Acme Corp...   │  │  La Boutique... │
│  Ton: amical"   │  │  Ton: formel"   │  │  Ton: chaleureux│
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## 5. Decision du LLM : Appeler ou Non le Tool

```
┌─────────────────────────────────────────────────────────────────┐
│              QUAND LE LLM APPELLE LE TOOL ?                     │
└─────────────────────────────────────────────────────────────────┘

Le LLM decide AUTOMATIQUEMENT d'appeler le tool base sur :

1. LE PROMPT SYSTEME
   → Lui indique qu'il a acces a un outil de recherche
   → Lui dit de TOUJOURS l'utiliser pour les questions factuelles

2. LA NATURE DE LA QUESTION
   → Questions sur les produits, prix, politiques → APPEL
   → Salutations, remerciements, reformulations → PAS D'APPEL

3. LE CONTEXTE DE LA CONVERSATION
   → Si l'info est deja dans l'historique → peut-etre pas d'appel
   → Nouvelle question factuelle → APPEL


     Question de l'utilisateur
              │
              ▼
    ┌─────────────────┐
    │ Le LLM analyse  │
    │ la question     │
    └────────┬────────┘
              │
              ▼
    ┌─────────────────────────────────┐
    │ Necessite des infos factuelles? │
    └────────────────┬────────────────┘
              │
       ┌──────┴──────┐
       │             │
      OUI           NON
       │             │
       ▼             ▼
┌─────────────┐ ┌─────────────┐
│ APPEL TOOL  │ │ REPONSE     │
│ search_     │ │ DIRECTE     │
│ documents   │ │ (pas de     │
│             │ │  recherche) │
└─────────────┘ └─────────────┘
```

---

## 6. Resume du Workflow

| Etape | Composant | Action |
|-------|-----------|--------|
| 1 | Frontend | Envoie la requete avec company_id |
| 2 | Backend | Publie sur Redis inbox:{email} |
| 3 | Agent | Recoit le message, extrait company_id |
| 4 | Agent | Recupere config entreprise (PostgreSQL) |
| 5 | Agent | Cree/selectionne l'agent avec le bon prompt |
| 6 | LLM | Analyse la question |
| 7 | LLM | Decide d'appeler search_documents |
| 8 | Tool | Recherche vectorielle filtree par company_id |
| 9 | Tool | Formate les documents en contexte |
| 10 | LLM | Genere la reponse avec le contexte |
| 11 | Agent | Streame la reponse via Redis outbox:{email} |
| 12 | Frontend | Affiche la reponse en temps reel |

---

## 7. Fichiers Cles

| Fichier | Role |
|---------|------|
| `src/agents/simple_agent.py` | Orchestration de l'agent et gestion multi-tenant |
| `src/tools/rag_tools.py` | Definition du tool search_documents + RAGAgentState |
| `src/retrieval/retriever.py` | Logique de recherche avec filtre company_id |
| `src/retrieval/vector_store.py` | Interface avec pgvector |
| `src/repositories/company_repository.py` | Acces aux donnees entreprise |
| `src/config/settings.py` | Template de prompt personnalise |
| `backend/routes/chat.py` | Endpoint API avec company_id |

---

## 8. Architecture Technique (InjectedState)

### Passage du company_id au Tool

Le `company_id` est passe au tool `search_documents` via le mecanisme `InjectedState` de LangChain.
Cela evite les variables globales et garantit la thread-safety.

```
┌─────────────────────────────────────────────────────────────────┐
│              INJECTION DU COMPANY_ID DANS LE TOOL               │
└─────────────────────────────────────────────────────────────────┘

  1. Message recu avec company_id
         │
         ▼
  2. chat() prepare l'etat:
     input_state = {
         "messages": [...],
         "company_id": "techstore"  <-- Ajoute a l'etat
     }
         │
         ▼
  3. agent.astream(input_state)
         │
         ▼
  4. LLM appelle search_documents(query)
         │
         ▼
  5. LangChain injecte automatiquement l'etat:
     search_documents(query, state)
         │
         ▼
  6. Le tool accede au company_id:
     company_id = state["company_id"]  → "techstore"
```

### Schema d'etat personnalise

L'agent utilise un schema d'etat personnalise qui etend `AgentState` :

```
┌─────────────────────────────────────────────────────────────────┐
│                      RAGAgentState                              │
├─────────────────────────────────────────────────────────────────┤
│  messages: list      (herite de AgentState)                     │
│  company_id: str     (ajoute pour le multi-tenant)              │
└─────────────────────────────────────────────────────────────────┘
```

Ce schema est utilise de deux manieres :

1. **Dans `create_agent()`** : Definit la structure de l'etat
2. **Dans le tool** : Permet l'injection via `InjectedState`

### Avantages de cette architecture

| Aspect | Benefice |
|--------|----------|
| Thread-safe | Chaque requete a son propre etat, pas de partage |
| Testable | Etat explicite, facile a mocker dans les tests |
| Pas de variables globales | Evite les race conditions en environnement concurrent |
| Standard LangChain | Utilise les patterns recommandes par la documentation |
| Persistance | L'etat (dont company_id) est sauvegarde avec le checkpointer |

### Comparaison avec l'ancienne approche

```
AVANT (variables globales)              APRES (InjectedState)
─────────────────────────               ─────────────────────────
set_current_company_id()                input_state["company_id"]
       │                                        │
       ▼                                        ▼
Variable globale partagee               Etat par requete
       │                                        │
       ▼                                        ▼
get_current_company_id()                state["company_id"]
       │                                        │
       ▼                                        ▼
   RISQUE: Race conditions              SECURISE: Thread-safe
```
