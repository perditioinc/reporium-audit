# $0 / OSS / local-only dev substrate for reporium-audit.
# Usage: make up && make smoke && make down
#
# Requires: docker + docker compose, python3 (for fixture generation).

COMPOSE := docker compose
PYTHON  := python3

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

.PHONY: seed
seed: ## Generate fixtures and create .env from .env.example
	$(PYTHON) scripts/gen_fixtures.py
	$(PYTHON) scripts/gen_github_fixtures.py
	@if [ ! -f .env ]; then cp .env.example .env; echo "created .env from .env.example"; else echo ".env already exists -- left as-is"; fi

.PHONY: up
up: seed ## Seed fixtures, build, and start the substrate (waits for healthy)
	$(COMPOSE) up --build --wait substrate

.PHONY: smoke
smoke: ## Run the real audit against local substitutes and assert no failures
	$(COMPOSE) run --rm --build audit "/bin/sh /scripts/smoke.sh"

.PHONY: down
down: ## Stop and remove containers, networks, and volumes
	$(COMPOSE) down -v --remove-orphans

.PHONY: teardown
teardown: down ## Alias for down: full teardown including volumes
	@echo "teardown complete"

.PHONY: logs
logs: ## Tail substrate logs
	$(COMPOSE) logs -f substrate
