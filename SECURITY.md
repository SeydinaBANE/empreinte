# Securite, souverainete & RGPD

## Souverainete des donnees

Empreinte est concu pour traiter des documents RSE confidentiels **sans egress**. En mode
souverain (`EMPREINTE_SOVEREIGN_MODE=true`, defaut), `assert_sovereign_endpoint` interdit
tout endpoint LLM public : seuls des hotes prives (localhost, IP privees, `.local`, services
Docker) sont autorises. Le mode demo n'effectue aucun appel reseau.

## Authentification & autorisation

- Toutes les routes metier exigent `X-API-Key` ; `/health` est public.
- RBAC a deux roles (`analyst`, `auditor`) — voir `docs/couche-06-gouvernance-souverainete.md`.
- Rate limiting par IP sur les routes `/chat*`.

## Donnees personnelles (RGPD)

- `mask_pii` masque emails et IBAN dans les reponses de chat.
- Aucune persistance externe : les documents uploades restent en memoire (`DocumentStore`)
  pour la duree de vie du process.
- Journal d'audit append-only de chaque acces (`AuditLog`).

## Secrets

- Aucun secret en dur ; configuration via variables d'environnement (`EMPREINTE_*`).
- `detect-secrets` (hook pre-commit + `make security`) avec baseline `.secrets.baseline`.
- `pip-audit` pour les vulnerabilites de dependances.

## Signalement

Pour signaler une vulnerabilite, ouvrir une issue privee ou contacter le mainteneur. Merci
de ne pas divulguer publiquement avant correction.
