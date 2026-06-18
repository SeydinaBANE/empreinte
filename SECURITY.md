# Securite, souverainete & RGPD

## Souverainete des donnees

Empreinte est concu pour traiter des documents RSE confidentiels **sans egress**. En mode
souverain (`EMPREINTE_SOVEREIGN_MODE=true`, defaut), `assert_sovereign_endpoint` interdit
tout endpoint LLM public : seuls des hotes prives (localhost, IP privees, `.local`, services
Docker) sont autorises. Le mode demo n'effectue aucun appel reseau.

## Authentification & autorisation

- **Mode `api_key`** (demo) : header `X-API-Key` mappe vers un role + tenant par defaut.
- **Mode `jwt`** (prod, OIDC) : jeton porteur valide (signature RS256/JWKS ou HS256, issuer,
  audience) ; les claims fournissent les roles et le `tenant_id`.
- RBAC : `analyst` (extract, chat), `auditor` (+ report, erase). `/health`, `/ready`,
  `/metrics` publics.
- Rate limiting par IP sur les routes `/chat*`.

## Isolation multi-tenant

- Chaque donnee porte un `tenant_id` ; documents et bilans sont **filtres par tenant** en
  base, et les images sont prefixees par tenant dans le stockage objet.
- Un appelant ne peut lire/effacer que les donnees de son tenant (verifie dans les depots).

## Donnees personnelles (RGPD)

- `mask_pii` masque emails et IBAN dans les reponses de chat.
- **Droit a l'effacement** : `DELETE /documents/{id}` supprime document, bilan et images du
  tenant (role `auditor`).
- **Retention** : `scripts/purge_retention.py` (CronJob) purge les documents au-dela de
  `EMPREINTE_RETENTION_DAYS`.
- **Chiffrement** : at-rest (Postgres TDE + chiffrement bucket SSE) et in-transit (TLS/mTLS
  in-cluster) — assures par l'infra (cf. `docs/couche-09-persistance-deploiement.md`).
- Journal d'audit de chaque acces (`AuditLog`). *Persistance de l'audit en base : prevue (le
  chemin d'audit reste en memoire a ce stade).*

## Secrets

- Aucun secret en dur ; configuration via variables d'environnement (`EMPREINTE_*`).
- `detect-secrets` (hook pre-commit + `make security`) avec baseline `.secrets.baseline`.
- `pip-audit` pour les vulnerabilites de dependances.

## Signalement

Pour signaler une vulnerabilite, ouvrir une issue privee ou contacter le mainteneur. Merci
de ne pas divulguer publiquement avant correction.
