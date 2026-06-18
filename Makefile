.PHONY: help init install-dev install-prod lint lint-fix format typecheck test \
        test-coverage precommit precommit-all security docker-build docker-up \
        docker-down docker-logs build clean all

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

init: ## Initialise l'environnement complet (venv + deps + hooks)
	python3 -m venv .venv && \
	. .venv/bin/activate && \
	pip install --upgrade pip setuptools wheel && \
	pip install -e ".[dev,test]" && \
	pre-commit install --hook-type pre-commit --hook-type pre-push && \
	pre-commit run --all-files

install-dev: ## Installe les dependances de developpement
	pip install -e ".[dev,test]"

install-prod: ## Installe les dependances de production uniquement
	pip install -e "."

lint: ## Verifie le code avec ruff
	ruff check src/ tests/

lint-fix: ## Corrige automatiquement les erreurs ruff
	ruff check --fix src/ tests/

format: ## Formate le code avec ruff
	ruff format src/ tests/

typecheck: ## Verifie les types avec mypy
	mypy src/

test: ## Execute les tests unitaires
	python3 -m pytest tests/

test-coverage: ## Execute les tests avec rapport HTML
	python3 -m pytest tests/ --cov-report=html --cov-report=term

precommit: ## Execute pre-commit sur les fichiers modifies
	pre-commit run

precommit-all: ## Execute pre-commit sur tous les fichiers
	pre-commit run --all-files

security: ## Verifie les secrets et vulnerabilites
	detect-secrets scan --baseline .secrets.baseline
	pip-audit

docker-build: ## Construit l'image Docker
	docker build -t empreinte:latest .

docker-up: ## Demarre la stack locale complete
	docker compose up -d --build

docker-down: ## Arrete la stack locale
	docker compose down -v

docker-logs: ## Affiche les logs Docker
	docker compose logs -f

build: lint typecheck test ## Execute toutes les verifications avant build

clean: ## Nettoie les artefacts locaux
	rm -rf .venv/ .mypy_cache/ .ruff_cache/ .pytest_cache/ \
	       __pycache__/ */__pycache__/ */*/__pycache__/ \
	       htmlcov/ .coverage *.egg-info/ dist/ build/

all: init build ## Initialise et verifie tout le projet
