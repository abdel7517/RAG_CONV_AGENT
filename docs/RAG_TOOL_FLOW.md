# RAG Tool Flow - search_documents

## Vue d'ensemble

Le tool `search_documents` permet à l'agent LangChain de rechercher des informations dans la base de documents vectorielle (pgvector). C'est le mécanisme central du RAG (Retrieval Augmented Generation).

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FLUX D'APPEL DU TOOL                          │
└─────────────────────────────────────────────────────────────────────────┘

  User: "Quels sont les produits disponibles ?"
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  1. SimpleAgent.chat()                                                  │
│     - Reçoit le message utilisateur                                     │
│     - Appelle agent.astream() avec le message                          │
└─────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  2. LangGraph Agent (créé par create_agent)                            │
│     - Analyse le message avec le LLM (Mistral/Ollama)                  │
│     - Le LLM DÉCIDE s'il doit utiliser un tool                         │
│     - Si la question nécessite des infos des documents → appelle tool  │
└─────────────────────────────────────────────────────────────────────────┘
                    │
                    │  Le LLM génère un "tool call" avec:
                    │  - name: "search_documents"
                    │  - args: {"query": "produits disponibles"}
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  3. search_documents(query)          [src/tools/rag_tools.py:34]       │
│     - Fonction décorée avec @tool                                       │
│     - Récupère le Retriever global                                      │
│     - Appelle retriever.retrieve_formatted(query)                       │
└─────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  4. Retriever.retrieve_formatted()   [src/retrieval/retriever.py:81]   │
│     - Appelle retrieve() puis format_documents()                        │
└─────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  5. Retriever.retrieve()             [src/retrieval/retriever.py:25]   │
│     - Appelle vector_store.similarity_search(query, k)                  │
│     - k = nombre de documents à retourner (défaut: 4)                   │
└─────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  6. VectorStore.similarity_search()  [src/retrieval/vector_store.py]   │
│     - Convertit la query en embedding (vecteur)                         │
│     - Recherche les k vecteurs les plus proches dans pgvector           │
│     - Retourne les Documents correspondants                             │
└─────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  7. Retriever.format_documents()     [src/retrieval/retriever.py:54]   │
│     - Formate les documents en texte lisible                            │
│     - Inclut: source, page, contenu                                     │
│     - Retourne une string formatée                                      │
└─────────────────────────────────────────────────────────────────────────┘
                    │
                    │  Résultat retourné au LLM:
                    │  "[Document 1]
                    │   Source: produits.pdf (page 3)
                    │   Contenu: Nos produits incluent..."
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  8. LangGraph Agent                                                     │
│     - Reçoit le résultat du tool                                        │
│     - Le LLM utilise ce contexte pour générer sa réponse                │
│     - Génère la réponse finale en streaming                             │
└─────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
  Assistant: "D'après notre documentation, les produits disponibles sont..."
```

## Quand le tool est-il appelé ?

Le LLM décide **automatiquement** d'appeler le tool basé sur:

1. **Le system prompt** (`SYSTEM_PROMPT_RAG` dans settings.py) qui lui indique qu'il a accès à un outil de recherche
2. **La nature de la question** - si elle nécessite des informations factuelles sur les documents
3. **Le contexte de la conversation**

### Exemples où le tool EST appelé:
- "Quels sont vos produits ?"
- "Quelle est votre politique de retour ?"
- "Combien coûte le produit X ?"

### Exemples où le tool N'EST PAS appelé:
- "Bonjour, comment ça va ?"
- "Merci pour l'info"
- "Peux-tu reformuler ?"

## Fichiers impliqués

| Fichier | Rôle |
|---------|------|
| `src/tools/rag_tools.py` | Définition du tool `search_documents` |
| `src/retrieval/retriever.py` | Logique de recherche et formatage |
| `src/retrieval/vector_store.py` | Interface avec pgvector |
| `src/agents/simple_agent.py` | Création de l'agent avec le tool |
| `src/config/settings.py` | `SYSTEM_PROMPT_RAG` qui guide le LLM |

## Configuration dans SimpleAgent

```python
# src/agents/simple_agent.py

def _setup_rag(self):
    """Configure les composants RAG si activé."""
    if not self.enable_rag:
        return

    # 1. Crée le VectorStore (connexion à pgvector)
    self.vector_store = VectorStore()

    # 2. Crée le Retriever (wrapper pour la recherche)
    self.retriever = Retriever(self.vector_store)

    # 3. Crée le tool et l'associe au retriever
    self.search_tool = create_search_documents_tool(self.retriever)

def _create_agent(self):
    """Crée l'agent LangGraph."""
    # Le tool est passé à l'agent seulement si RAG est activé
    tools = [self.search_tool] if self.enable_rag and self.search_tool else []

    # Le prompt RAG indique au LLM comment utiliser le tool
    system_prompt = settings.SYSTEM_PROMPT_RAG if self.enable_rag else settings.SYSTEM_PROMPT

    self.agent = create_agent(
        model=self.llm,
        tools=tools,  # <-- Le tool est enregistré ici
        system_prompt=system_prompt,
        checkpointer=self.memory
    )
```

## Le décorateur @tool

```python
# src/tools/rag_tools.py

@tool  # <-- Ce décorateur transforme la fonction en "Tool" LangChain
def search_documents(query: str) -> str:
    """
    Permet de retrouver des informations en lien avec le commerçant comme 
    les CGU, CGV .. (délais de livraison, de retour..)
    Recherche des informations pertinentes dans la base de documents.

    Args:
        query: La question ou les mots-clés à rechercher

    Returns:
        Les extraits de documents pertinents formatés
    """
    retriever = get_retriever()
    result = retriever.retrieve_formatted(query)
    return result
```

## Format de la réponse du tool

Le tool retourne une string formatée comme ceci:

```
[Document 1]
Source: TechStore_Documentation.pdf (page 3)
Contenu:
Nos produits phares incluent:
- Smartphone TechX Pro: 899€
- Laptop UltraBook 15: 1299€
- Tablette TabMax: 599€

---

[Document 2]
Source: TechStore_Documentation.pdf (page 5)
Contenu:
Politique de garantie:
Tous nos produits sont garantis 2 ans...
```

Ce texte est ensuite injecté dans le contexte du LLM qui l'utilise pour formuler sa réponse finale.

## Debug / Logs

Pour voir quand le tool est appelé, active les logs DEBUG:

```python
# Dans main.py, le logging est déjà configuré en DEBUG
logging.basicConfig(level=logging.DEBUG, ...)
```

Tu verras dans les logs:
```
INFO - Tool search_documents appelé avec: 'produits disponibles...'
INFO - Recherche de documents pour: 'produits disponibles...'
INFO -   -> 4 documents trouves
DEBUG - Résultat de la recherche: 1523 caractères
```
