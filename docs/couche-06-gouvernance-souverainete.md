# Couche 06 — Gouvernance & souverainete

## Role

Garantir que les donnees RSE confidentielles restent maitrisees : controle d'acces,
non-fuite vers l'exterieur, masquage des donnees personnelles, tracabilite.

## Module

`src/empreinte/governance.py`

## RBAC

| Role | Permissions |
|---|---|
| `analyst` | `EXTRACT`, `CHAT` |
| `auditor` | `EXTRACT`, `REPORT`, `CHAT` |

`RBACPolicy.authorize` leve `AccessDeniedError` si la permission manque (→ HTTP 403).

## Souverainete des donnees

`assert_sovereign_endpoint(api_base, sovereign_mode)` : en mode souverain
(`EMPREINTE_SOVEREIGN_MODE=true`), l'endpoint LLM doit etre **prive**. Sont autorises :
`localhost`, `127.0.0.1`/`::1`, IP privees (`10.`, `192.168.`, `172.1x.`), domaines `.local`
et hostnames mono-label (services Docker comme `ollama`). Tout FQDN public (ex.
`api.openai.com`) leve `SovereigntyError`. Le mode demo (`api_base` vide) ne fait aucun
appel reseau.

## Masquage PII

`mask_pii` masque emails et IBAN susceptibles d'apparaitre dans des documents fournisseurs,
applique sur les reponses de chat.

## Audit

`AuditLog` enregistre chaque action (utilisateur, action, ressource, autorise/refuse) en
journal append-only, trace en JSON via structlog.
