# Couche 09 — Persistance & déploiement (production)

## Persistance

L'état n'est plus en mémoire : un Protocol découple le stockage de l'application.

| Composant | Demo / tests | Production |
|---|---|---|
| Documents (métadonnées) | `InMemoryDocumentRepository` | `SqlDocumentRepository` (Postgres) |
| Images de pages | en mémoire | stockage objet S3/MinIO (`S3ObjectStore`) |
| Bilans | `InMemoryReportRepository` | `SqlReportRepository` (Postgres) |

- Modules : `repositories.py`, `object_store.py`. Les binaires vont dans le stockage objet,
  seules les **clés** sont persistées en base.
- Sélection par configuration dans `services.py::_build_repositories` (même logique que
  `_build_retriever`) : `EMPREINTE_SQL_DSN` + `EMPREINTE_OBJECT_STORE_ENDPOINT` renseignés →
  chemin SQL+objet, sinon mémoire.
- **Migrations** : Alembic (`alembic/`). `alembic upgrade head` crée `documents`,
  `document_pages`, `reports`. Joué en hook Helm `pre-install/pre-upgrade` et par le service
  `migrate` de `docker-compose`.

## Observabilité

- `/health` (liveness), `/ready` (readiness : vérifie Postgres, Qdrant, vLLM configurés).
- `/metrics` : exposition Prometheus (`empreinte_events_total`, `empreinte_span_duration_ms`)
  alimentée par `observability.METRICS` / `record_span`.

## RAG réglementaire en production

`scripts/index_corpus.py` indexe `empreinte.corpus.ESRS_CORPUS` dans Qdrant (embeddings
fastembed locaux, souverains). `QdrantRetriever` interroge cette collection.

## Déploiement (cloud privé / VPC + GPU)

- **Stack locale** : `docker compose up` (app + Postgres + MinIO + Qdrant + Ollama + migrate)
  — permet de vérifier la persistance (uploader, redémarrer, retrouver le document).
- **Helm** : `deploy/helm/empreinte` (Deployment + HPA + Service + Ingress TLS + ConfigMap +
  ServiceMonitor + Job de migration). Valeurs par env : `values-staging.yaml`, `values-prod.yaml`.
  Secrets via secret externe (`existingSecret`), jamais en clair.
- **vLLM** : `deploy/vllm/vllm-deployment.yaml` sur node pool GPU, Service in-cluster `vllm`.
  Souveraineté préservée (`assert_sovereign_endpoint` accepte `*.svc.cluster.local`).
- **CI/CD** : `ci.yml` (qualité + build + push image GHCR) ; `deploy.yml` (OIDC vers le
  cluster VPC + `helm upgrade`, migrations jouées en hook).
