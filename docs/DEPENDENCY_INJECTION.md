# Dependency Injection avec dependency-injector

Ce document explique l'architecture d'injection de dépendances utilisée dans le projet.

## Table des matières

1. [Introduction](#introduction)
2. [Le Container](#le-container)
3. [Le Wiring](#le-wiring-concept-clé)
4. [@inject + Provide[]](#inject--provide)
5. [Tests avec Override](#tests-avec-override)
6. [Architecture Hexagonale](#architecture-hexagonale)

---

## Introduction

### Qu'est-ce que dependency-injector ?

[dependency-injector](https://python-dependency-injector.ets-labs.org/) est une librairie Python qui fournit :

- **Providers déclaratifs** : `Singleton`, `Factory`, `Configuration`
- **Wiring automatique** : Connecte le container aux modules Python
- **Override pour tests** : Remplace les dépendances sans modifier le code

### Pourquoi l'utiliser ?

| Aspect | Sans DI | Avec dependency-injector |
|--------|---------|--------------------------|
| Création d'objets | `service = RAGService()` partout | `container.rag_service()` |
| Singleton | Variable de classe manuelle | `providers.Singleton` automatique |
| Tests | Modifier le constructeur | `container.override()` |
| Dépendances | Implicites dans le code | Explicites dans le Container |

---

## Le Container

Le container est une classe déclarative qui définit toutes les dépendances :

```python
# src/infrastructure/container.py

from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    """Container DI déclaratif."""

    # Adapters (Singleton = une seule instance)
    vector_store = providers.Singleton(PGVectorAdapter)

    retriever = providers.Singleton(
        LangChainRetrieverAdapter,
        vector_store=vector_store  # Injection automatique
    )

    # Service
    rag_service = providers.Singleton(
        RAGService,
        retriever=retriever  # Injection automatique
    )
```

### Graphe de dépendances

```
rag_service
    └── retriever
            └── vector_store
```

Quand on appelle `container.rag_service()`, le container :
1. Crée `vector_store` (Singleton)
2. L'injecte dans `retriever`
3. Injecte `retriever` dans `rag_service`
4. Retourne l'instance

---

## Le Wiring (concept clé)

### À quoi sert `wire()` ?

Le **wiring** connecte le container aux modules Python pour que `@inject` fonctionne.

### Sans wire() → `@inject` ne fonctionne PAS

```python
@inject
def _setup_rag(
    self,
    rag_service: RAGService = Provide[Container.rag_service]
):
    print(rag_service)  # ❌ None - pas injecté !
```

### Avec wire() → `@inject` fonctionne

```python
# Au démarrage (main.py)
container = Container()
container.wire(modules=["src.agents.simple_agent"])

# Maintenant @inject fonctionne
@inject
def _setup_rag(
    self,
    rag_service: RAGService = Provide[Container.rag_service]
):
    print(rag_service)  # ✅ <RAGService instance>
```

### Comment ça fonctionne techniquement ?

`wire()` fait du **monkey-patching** sur le module cible :

1. Il scanne le module `src.agents.simple_agent`
2. Il trouve les fonctions décorées avec `@inject`
3. Il remplace `Provide[Container.rag_service]` par l'appel réel `container.rag_service()`

```
AVANT wire():
  Provide[Container.rag_service] → Marqueur (placeholder vide)

APRÈS wire():
  Provide[Container.rag_service] → container.rag_service() (appel réel)
```

### Où placer le wire() ?

**Option recommandée** : Au début du point d'entrée (`main.py`)

```python
# main.py - AU DÉBUT DU FICHIER

from src.infrastructure.container import Container

# Container global + wire immédiat
container = Container()
container.wire(modules=["src.agents.simple_agent"])
```

Le wire se fait une seule fois au démarrage, puis `@inject` fonctionne partout dans les modules wirés.

---

## @inject + Provide[]

### Syntaxe

```python
from dependency_injector.wiring import inject, Provide
from src.infrastructure.container import Container

class SimpleAgent:

    @inject
    def _setup_rag(
        self,
        rag_service: RAGService = Provide[Container.rag_service]
    ):
        """Le rag_service est injecté automatiquement."""
        self.rag_service = rag_service
```

### Flow d'exécution

```
┌─────────────────────────────────────────────────────────────┐
│  1. main.py démarre                                         │
│     container.wire(modules=["src.agents.simple_agent"])     │
│     → Connecte @inject au container                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  2. agent._setup_rag() est appelé                           │
│                                                             │
│     @inject détecte Provide[Container.rag_service]          │
│     → Remplace par container.rag_service()                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Container résout les dépendances                        │
│                                                             │
│     rag_service                                             │
│         └── retriever                                       │
│                 └── vector_store                            │
│                                                             │
│     → Crée les Singletons si pas encore créés               │
│     → Retourne l'instance RAGService                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  4. rag_service = <RAGService instance>  ✅                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Tests avec Override

### Principe

`override()` permet de remplacer une dépendance sans modifier le code de production :

```python
from unittest.mock import Mock
from src.infrastructure.container import Container
from src.domain.ports.retriever_port import RetrieverPort

def test_rag_service():
    container = Container()

    # Créer un mock du retriever
    mock_retriever = Mock(spec=RetrieverPort)
    mock_retriever.retrieve_formatted.return_value = "Résultat mocké"

    # Override sans toucher au code de production
    with container.retriever.override(mock_retriever):
        service = container.rag_service()
        result = service.search_formatted("test query")

        assert result == "Résultat mocké"
        mock_retriever.retrieve_formatted.assert_called_once()
```

### Avantages

- **Pas de modification du code** de production
- **Isolation** : Le mock n'affecte que le scope du `with`
- **Composition** : On peut override plusieurs providers

---

## Architecture Hexagonale

Le container s'intègre dans l'architecture hexagonale :

```
┌─────────────────────────────────────────────────────────────┐
│                    DOMAIN (Ports)                           │
│                                                             │
│   VectorStorePort (ABC)      RetrieverPort (ABC)           │
│   - similarity_search()      - retrieve()                   │
│   - similarity_search_with_score()  - retrieve_formatted()  │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ implémente
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 INFRASTRUCTURE (Adapters)                   │
│                                                             │
│   PGVectorAdapter            LangChainRetrieverAdapter      │
│   (implémente VectorStorePort)  (implémente RetrieverPort)  │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ injecté via Container
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 APPLICATION (Services)                      │
│                                                             │
│   RAGService                                                │
│   - Dépend de RetrieverPort (interface)                     │
│   - Ne connaît pas l'implémentation concrète                │
└─────────────────────────────────────────────────────────────┘
```

### Changer d'implémentation

Pour utiliser Pinecone au lieu de PGVector :

1. Créer `PineconeAdapter` qui implémente `VectorStorePort`
2. Modifier le container :

```python
# Avant
vector_store = providers.Singleton(PGVectorAdapter)

# Après
vector_store = providers.Singleton(PineconeAdapter)
```

**Aucun autre changement nécessaire** - le reste du code utilise l'interface.

---

## Résumé

| Concept | Description |
|---------|-------------|
| **Container** | Définit les dépendances de manière déclarative |
| **Providers** | `Singleton`, `Factory` - gèrent le cycle de vie |
| **wire()** | Connecte le container aux modules pour `@inject` |
| **@inject** | Décorateur pour l'injection automatique |
| **Provide[]** | Marqueur pour indiquer quelle dépendance injecter |
| **override()** | Remplace une dépendance pour les tests |
