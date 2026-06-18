# Couche 07 — API

## Role

Exposer le pipeline en HTTP, sous controle d'acces, avec arret gracieux et observabilite.

## Modules

`src/empreinte/api.py`, `dependencies.py`, `middleware.py`

## Endpoints

| Methode | Route | Permission | Description |
|---|---|---|---|
| GET | `/health` | — (public) | Sante du service |
| POST | `/documents` | `EXTRACT` | Upload (PDF/image) → `doc_id` |
| POST | `/extract` | `EXTRACT` | Donnees d'activite extraites d'un document |
| POST | `/report` | `REPORT` | Bilan carbone sourcé |
| POST | `/chat` | `CHAT` | Question reglementaire ESRS (reponse sourcée) |
| POST | `/chat/stream` | `CHAT` | Idem en SSE |

## Authentification

Header `X-API-Key` obligatoire (sauf `/health`). Cles → roles via `EMPREINTE_API_KEYS`.
Header manquant → `422`, clé invalide → `401`, permission insuffisante → `403`, document
inconnu → `404`.

## Middlewares

- Rate limiting par IP (fenetre glissante) sur les routes `/chat*`.
- Correlation ID (`X-Request-ID`) propage et lie aux logs structlog.

## Robustesse

- `lifespan` : fermeture des clients HTTP async a l'arret.
- Gestionnaire d'exception global : toute erreur non geree → `500` neutre, sans fuite
  d'information (la trace reste dans les logs).
