# Empreinte — agent instructions

Python 3.12+ FastAPI GenAI multimodal on-premise pour le reporting ESG/CSRD (extraction
vision, taxonomie ESRS, bilan carbone deterministe).

## Setup & commands

```bash
make init        # .venv + pip install -e ".[dev,test]" + pre-commit hooks
cp .env.example .env
make docker-up   # app + Qdrant + Ollama (VLM)
```

Order before push: `make build` (= lint + typecheck + test). CI runs the same plus
`ruff format --check` and `pytest --cov-fail-under=80`.

| Command | What |
|---|---|
| `make lint` | `ruff check src/ tests/` |
| `make format` | `ruff format src/ tests/` |
| `make typecheck` | `mypy src/` (strict + pydantic plugin) |
| `make test` | `pytest tests/` (asyncio_mode=auto, auto-coverage) |
| `make security` | `detect-secrets scan` + `pip-audit` |

Run a single test: `pytest tests/test_factors.py -k test_compute_line_electricity_scope_2`.

## Architecture

- Package `empreinte` under `src/` (imports are `from empreinte.xxx import …`)
- **Entrypoint:** `empreinte.api:app` (FastAPI)
- **Config:** pydantic-settings, prefix `EMPREINTE_`, loaded from `.env` — see `config.py`
- **Pipeline flow:** upload → `ingestion` (PDF/image → pages) → `extraction` (VLM → indicateurs)
  → `taxonomy` (rattachement ESRS) → `factors` (moteur carbone) → `report` (bilan sourcé)
- **Gateway** (`gateway.py`): `VisionLLMProvider` (Protocol) ; `LocalVisionProvider`
  deterministe (offline/tests, JSON canné pour les images), `OpenAICompatVisionProvider`
  (vLLM/Ollama via httpx, contenu multimodal), primaire + fallback
- **Carbone** (`factors.py`): catalogue de facteurs + `CarbonEngine` **deterministe** —
  le LLM n'effectue aucun calcul d'emission
- **Taxonomie** (`taxonomy.py`): mapping explicite categorie d'activite → point de donnee ESRS
- **RAG** (`retriever.py`): `InMemoryRetriever` (lexical, demo) / `QdrantRetriever` (prod)
- **Assistant** (`assistant.py`): questions reglementaires ESRS ancrees sur le corpus
- **Gouvernance** (`governance.py`): RBAC, `mask_pii`, `assert_sovereign_endpoint`, `AuditLog`
- **Persistance** (`repositories.py`, `object_store.py`): `DocumentRepository` /
  `ReportRepository` (Protocol) — InMemory (demo/tests) ou SQL (Postgres async) +
  `ObjectStore` (InMemory / S3-MinIO). Migrations Alembic (`alembic/`).
- **Composition root** (`services.py`): `build_pipeline()` — demo (LocalVisionProvider +
  InMemoryRetriever + repos memoire) vs prod (vLLM + Qdrant + Postgres + objet) ;
  `check_readiness()` pour `/ready`
- **Observabilite** (`observability.py`): `METRICS`/`record_span` exposes en Prometheus
  (`/metrics`) ; endpoints `/health` (live) et `/ready` (backends)
- **Middlewares** (`middleware.py`): rate limiting par IP, correlation ID
- **Deploiement** (`deploy/`): chart Helm + manifeste vLLM GPU ; `scripts/index_corpus.py`

## API auth

- `X-API-Key` requis sur `/documents`, `/extract`, `/report`, `/chat`, `/chat/stream`
- Cles dans `EMPREINTE_API_KEYS` (format `key:role,key:role`)
- Roles : `analyst` (extract + chat), `auditor` (extract + report + chat)
- Header manquant → `422`, clé invalide → `401`, permission insuffisante → `403`
- `/health` public ; rate limiting sur les routes `/chat*`

## Souverainete (mode `EMPREINTE_SOVEREIGN_MODE=true`)

- `assert_sovereign_endpoint` refuse tout endpoint LLM public (FQDN avec point) ; seuls les
  hotes prives sont autorises : `localhost`, IP privees, `*.local`, hostnames mono-label
  (services Docker comme `ollama`)
- Mode demo (`EMPREINTE_LLM_API_BASE` vide) : aucun appel reseau

## Testing conventions

- **No external services needed** — `ScriptedVisionProvider` + `make_gateway(reply)` dans
  `conftest.py` ; `httpx.MockTransport` pour `OpenAICompatVisionProvider`
- Les images de test sont des PNG factices base64 (le provider local ignore leur contenu)
- `pytest -m integration` pour les tests necessitant vLLM/Qdrant

## Style

- Ruff line-length 100, target py312, no `Any`/`dict`/`list` without concrete types
- Python 3.12 syntax (`Annotated`, `StrEnum`, `Protocol`, `frozenset`)
- structlog JSON logging (use `get_logger(__name__)`), no `print`
- No comments in code — code must be self-documenting
- `pre-commit` runs ruff lint/format, mypy, detect-secrets
