# Couche 08 — Tests & qualite

## Principe

Tout est testable **hors-ligne** : aucun GPU, aucun service externe requis pour `make test`.

## Outils de substitution

- `ScriptedVisionProvider` + `make_gateway(reply)` (`conftest.py`) : reponses LLM
  deterministes.
- `httpx.MockTransport` : teste `OpenAICompatVisionProvider` (complete, stream, multimodal,
  erreurs HTTP) sans reseau.
- Images de test : PNG factices base64 (le provider local ignore leur contenu).

## Couverture

`make build` impose lint (ruff) + typecheck (mypy strict) + tests. CI ajoute
`pytest --cov-fail-under=80`. Couverture actuelle : **92 %** (58 tests).

## Repartition

| Suite | Cible |
|---|---|
| `test_factors.py` | Moteur carbone, conversions d'unites, agregation, erreurs |
| `test_taxonomy.py` | Mapping ESRS |
| `test_gateway.py` | Provider local, fallback, provider HTTP, SSE |
| `test_ingestion.py` | Encodage pages, erreurs |
| `test_extraction.py` | Parsing JSON defensif, rejet d'items invalides |
| `test_retriever.py` | Scoring lexical, top_k, requete vide |
| `test_report.py` | Bilan, totaux, repli narratif |
| `test_assistant.py` | Reponse RAG, repli, streaming |
| `test_governance.py` | RBAC, souverainete, masquage PII, audit |
| `test_services.py` | Composition root, demo, document store |
| `test_api.py` | Bout en bout en mode demo (auth, RBAC, 404) |

## Tests d'integration

`pytest -m integration` : reserves aux scenarios necessitant vLLM/Qdrant reels.
