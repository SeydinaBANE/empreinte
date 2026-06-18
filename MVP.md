# MVP

## Objectif

Une application complete, industrialisable, demontrant les 3 differenciateurs : multimodal,
on-premise/souverain, calcul deterministe auditable — dans le domaine ESG/CSRD.

## Perimetre livré

- **Ingestion** PDF/image → pages-images (extra `pdf` via pypdfium2).
- **Extraction multimodale** : gateway vision (local deterministe + OpenAI-compatible
  vLLM/Ollama), parsing JSON defensif.
- **Taxonomie ESRS** explicite, **moteur carbone** deterministe (7 categories, 3 scopes).
- **Bilan sourcé** + narration ancree, **assistant RAG** reglementaire (InMemory/Qdrant).
- **Gouvernance** : RBAC, souverainete (no egress), masquage PII, audit.
- **API** FastAPI complete (`/documents`, `/extract`, `/report`, `/chat`, `/chat/stream`,
  `/health`), middlewares (rate limit, correlation ID), arret gracieux.
- **Industrialisation** : pyproject (ruff/mypy strict), Makefile, Docker + Compose
  (app + Qdrant + Ollama), CI GitHub Actions, pre-commit, detect-secrets.

## Qualite

- `make build` vert : ruff + mypy strict + 58 tests.
- Couverture **92 %** (seuil CI 80 %).
- Mode demo entierement hors-ligne (aucun GPU ni service externe requis).

## Hors perimetre (cf. ROADMAP)

Export CSRD (XBRL), referentiel ADEME complet, eval d'extraction en CI, validation humaine
dans la boucle, deploiement GPU.
