<p align="center">
  <img src="https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/multimodal-VLM-7B2FF7" alt="Multimodal">
  <img src="https://img.shields.io/badge/on--premise-souverain-2ea44f" alt="On-premise">
  <img src="https://img.shields.io/badge/ruff-passing-00cc00?logo=ruff" alt="Ruff">
  <img src="https://img.shields.io/badge/mypy-strict-00cc00?logo=python" alt="Mypy">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</p>

<h1 align="center">Empreinte</h1>

<p align="center">
  Assistant GenAI <strong>multimodal on-premise</strong> pour le reporting ESG/CSRD —
  extraction vision de documents, taxonomie ESRS, bilan carbone deterministe et sourcé.
</p>

---

## A propos

**Empreinte** transforme des documents RSE heterogenes (factures d'energie, certificats
fournisseurs, rapports PDF avec tableaux et graphiques) en un **bilan carbone auditable**.
Un LLM vision (VLM) **on-premise** lit les pages et en extrait les donnees d'activite ;
celles-ci sont rattachees a la **taxonomie ESRS** puis converties en CO2e par un **moteur
deterministe** de facteurs d'emission. Aucune donnee ne quitte l'infrastructure.

| | |
|---|---|
| **Stack** | Python 3.12, FastAPI, Pydantic, httpx, structlog |
| **Multimodal** | Extraction vision (Qwen2.5-VL / Llama-3.2-Vision via vLLM ou Ollama) |
| **Souverainete** | Endpoint LLM prive impose en mode souverain, zero egress |
| **Coeur** | Moteur carbone deterministe (le LLM extrait, le moteur calcule) |
| **Gouvernance** | RBAC (analyst/auditor), masquage PII, audit, RAG reglementaire ESRS |
| **Infra** | Docker Compose (app + Qdrant + Ollama), CI GitHub Actions |

## Principe directeur — le LLM extrait, le moteur calcule

Les chiffres du bilan ne sont **jamais** produits par le modele : le VLM se limite a
extraire les donnees d'activite (kWh, litres, km…) ; un moteur pur applique les facteurs
d'emission. Resultat : des emissions **reproductibles, tracables et auditables**.

## Quick Start

```bash
make init        # venv + dependances + hooks pre-commit
cp .env.example .env
make docker-up   # app + Qdrant + Ollama (VLM on-premise)
```

API : http://localhost:8000/docs — par defaut en **mode demo hors-ligne** (provider
deterministe), aucun service externe requis.

```bash
# Bilan carbone du document de demo (role auditor)
curl -s http://localhost:8000/report \
  -H "X-API-Key: dev-key-auditor" -H "Content-Type: application/json" \
  -d '{"document_id": "demo-facture-energie"}'
```

## Commandes

```bash
make lint        # ruff
make typecheck   # mypy strict
make test        # pytest + couverture
make build       # lint + typecheck + test
```

## Documentation

| Fichier | Description |
|---|---|
| [PROJET.md](PROJET.md) | Vision, probleme, architecture |
| [docs/](docs/) | Une couche = un document (ingestion, extraction, taxonomie, moteur, RAG…) |
| [docs/adr/](docs/adr/) | Decisions d'architecture (ADR) |
| [SECURITY.md](SECURITY.md) | Securite, souverainete & RGPD |
| [ROADMAP.md](ROADMAP.md) · [POC.md](POC.md) · [MVP.md](MVP.md) | Planning |

## Licence

MIT — voir [LICENSE](LICENSE).
