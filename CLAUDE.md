# Instructions pour ce projet

## Règles de recherche d'information

- Pour TOUTE question concernant LangChain, LangGraph, ou les concepts associés,
  tu DOIS utiliser le MCP LangChain (SearchDocsByLangChain) AVANT de répondre.
- Ne te fie PAS à ta connaissance interne pour ces sujets.
- Cite toujours la source de la documentation.
- Si le MCP ne retourne pas de résultat, indique-le clairement.

## Sujets concernés
- LangChain
- LangGraph
- Agents LLM
- Chains
- Prompts templates LangChain
- Memory (LangChain)
- Tools et toolkits

## Règles de recherche dans le codebase

- Avant toute modification de code, utilise le MCP Serena (find_symbol,
  find_referencing_symbols, search_for_pattern, get_symbols_overview) pour
  rechercher les fichiers et références impactés.
- Ne modifie JAMAIS un symbole (classe, fonction, variable) sans avoir d'abord
  vérifié toutes ses références dans le projet via `find_referencing_symbols`.
- Cela permet d'éviter de casser des imports, des appels ou des dépendances
  existantes lors d'un renommage, d'une suppression ou d'un refactoring.