# Changelog

Format base sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
versionnage [SemVer](https://semver.org/lang/fr/).

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
