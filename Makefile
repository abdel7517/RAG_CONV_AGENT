# =============================================================================
# RAG Conversational Agent - Makefile
# =============================================================================

.PHONY: help build up down restart logs ps clean dev prod

# Couleurs
BLUE := \033[34m
GREEN := \033[32m
YELLOW := \033[33m
NC := \033[0m

help: ## Afficher cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "$(BLUE)%-15s$(NC) %s\n", $$1, $$2}'

# =============================================================================
# Development
# =============================================================================

dev: ## Lancer en mode developpement (avec hot reload)
	docker compose up -d postgres redis
	@echo "$(GREEN)Attente de la DB...$(NC)"
	@sleep 3
	docker compose up -d db-init
	@sleep 2
	docker compose up -d backend worker rag-agent

up: ## Lancer tous les services
	docker compose up -d

down: ## Arreter tous les services
	docker compose down

restart: ## Redemarrer backend, worker, rag-agent et frontend
	docker compose restart backend worker rag-agent

restart-backend: ## Redemarrer uniquement le backend
	docker compose restart backend

restart-worker: ## Redemarrer uniquement le worker
	docker compose restart worker

restart-rag: ## Redemarrer uniquement rag-agent
	docker compose restart rag-agent

restart-frontend: ## Redemarrer uniquement le frontend (avec rebuild) car l'image creer des fichier statiques qui contienne les var d'env lors du build
	docker compose up -d --build frontend

# =============================================================================
# Build
# =============================================================================

build: ## Builder toutes les images
	docker compose build

build-backend: ## Builder uniquement le backend
	docker compose build backend

build-frontend: ## Builder uniquement le frontend
	docker compose build frontend

build-no-cache: ## Builder sans cache
	docker compose build --no-cache

# =============================================================================
# Logs
# =============================================================================

logs: ## Voir les logs de tous les services
	docker compose logs -f

logs-backend: ## Voir les logs du backend
	docker compose logs -f backend

logs-worker: ## Voir les logs du worker
	docker compose logs -f worker

logs-rag: ## Voir les logs du rag-agent
	docker compose logs -f rag-agent

logs-db: ## Voir les logs de PostgreSQL
	docker compose logs -f postgres

# =============================================================================
# Status & Debug
# =============================================================================

ps: ## Voir le statut des containers
	docker compose ps

exec-backend: ## Shell dans le container backend
	docker compose exec backend sh

exec-db: ## Shell psql dans PostgreSQL
	docker compose exec postgres psql -U postgres -d agent_memory

# =============================================================================
# Cleanup
# =============================================================================

clean: ## Arreter et supprimer les containers
	docker compose down -v

prune: ## Nettoyer Docker (images, volumes non utilises)
	docker system prune -a --volumes -f

# =============================================================================
# Production
# =============================================================================

prod: ## Lancer en mode production
	docker compose up -d

prod-with-ollama: ## Lancer en production avec Ollama
	docker compose --profile ollama up -d

local: ## Lancer en local avec nginx frontend
	docker compose --profile local up -d

# =============================================================================
# Database
# =============================================================================

db-init: ## Initialiser la base de donnees
	docker compose up -d postgres
	@sleep 3
	docker compose run --rm db-init

db-reset: ## Reset la base de donnees (DANGER)
	docker compose down -v postgres_data
	docker compose up -d postgres
	@sleep 3
	docker compose run --rm db-init
