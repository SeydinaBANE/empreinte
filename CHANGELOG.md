# Changelog

Format base sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
versionnage [SemVer](https://semver.org/lang/fr/).

## [Unreleased] — Mise en production M1–M2

### Added (M2 — qualité & résilience)

- **Guided decoding** : `LLMRequest.response_schema` → `guided_json` vLLM ; schéma dérivé de
  Pydantic (`ExtractedIndicatorDraft`).
- **Seuil de confiance** : indicateurs `needs_review` sous `EMPREINTE_EXTRACTION_MIN_CONFIDENCE`.
- **Circuit breaker** dans `LLMGateway` (seuil d'échecs + cooldown, court-circuit vers fallback).
- **Harnais d'éval** : `evaluation.py` (P/R/F1 + exactitude numérique), `eval/` (dataset +
  `run_eval.py`), job CI `eval` non bloquant.



### Added

- **Persistance** : `DocumentRepository` / `ReportRepository` (Protocol) avec implémentations
  InMemory et SQL (SQLAlchemy 2.0 async / Postgres) ; `ObjectStore` (InMemory + S3/MinIO).
- **Migrations** Alembic (`documents`, `document_pages`, `reports`).
- **Observabilité** : endpoints `/ready` (readiness backends) et `/metrics` (Prometheus).
- **RAG production** : `scripts/index_corpus.py` (indexation Qdrant, embeddings fastembed).
- **Déploiement** : chart Helm (`deploy/helm/empreinte`), manifeste vLLM GPU
  (`deploy/vllm`), workflow `deploy.yml` + job `release` (push image GHCR), stack
  `docker-compose` enrichie (Postgres + MinIO + migrate).

## [0.1.0] — 2025

### Added

- Ingestion documentaire (image directe + rendu PDF optionnel via pypdfium2).
- Gateway LLM vision : provider local deterministe + provider OpenAI-compatible
  (vLLM/Ollama) avec contenu multimodal et fallback primaire/secondaire.
- Extraction multimodale avec parsing JSON defensif et rattachement ESRS.
- Taxonomie ESRS explicite (E1-5 energie, E1-6 GES).
- Moteur carbone deterministe (7 categories, 3 scopes, conversions d'unites).
- Bilan carbone sourcé avec narration ancree ; assistant RAG reglementaire
  (InMemory/Qdrant).
- Gouvernance : RBAC (analyst/auditor), souverainete (no egress), masquage PII, audit.
- API FastAPI (`/documents`, `/extract`, `/report`, `/chat`, `/chat/stream`, `/health`),
  rate limiting, correlation ID, arret gracieux.
- Outillage : ruff, mypy strict, pytest (couverture 92 %), Docker + Compose, CI, pre-commit.
