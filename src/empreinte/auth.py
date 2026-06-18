"""Authentification : verification de jeton JWT (OIDC) avec repli sur clé API.

En mode ``jwt`` (production), le jeton porteur est validé (signature, issuer, audience) et
ses claims fournissent les rôles et le ``tenant_id``. En mode ``api_key`` (démo), une clé
statique mappe vers un rôle et le tenant par défaut.
"""

from __future__ import annotations

import jwt

from empreinte.config import Settings
from empreinte.governance import Principal


class AuthError(RuntimeError):
    """Echec d'authentification (jeton invalide ou clé inconnue)."""


def _roles_from_claim(claim: object) -> frozenset[str]:
    if isinstance(claim, str):
        return frozenset(claim.split())
    if isinstance(claim, list):
        return frozenset(str(role) for role in claim)
    return frozenset()


def _decode(token: str, cfg: Settings) -> dict[str, object]:
    audience = cfg.jwt_audience or None
    issuer = cfg.jwt_issuer or None
    if cfg.jwt_algorithm == "HS256":
        return jwt.decode(
            token, cfg.jwt_secret, algorithms=["HS256"], audience=audience, issuer=issuer
        )
    signing_key = jwt.PyJWKClient(cfg.jwt_jwks_url).get_signing_key_from_jwt(  # pragma: no cover
        token
    )
    return jwt.decode(  # pragma: no cover
        token,
        signing_key.key,
        algorithms=[cfg.jwt_algorithm],
        audience=audience,
        issuer=issuer,
    )


def verify_jwt(token: str, cfg: Settings) -> Principal:
    """Valide un JWT et en derive le principal (user, rôles, tenant)."""
    try:
        claims = _decode(token, cfg)
    except jwt.PyJWTError as exc:
        raise AuthError(f"jeton invalide: {exc}") from exc
    roles = _roles_from_claim(claims.get(cfg.jwt_roles_claim))
    tenant = str(claims.get(cfg.jwt_tenant_claim) or cfg.default_tenant)
    subject = str(claims.get("sub") or "unknown")
    return Principal(user_id=subject, roles=roles, tenant_id=tenant)


def principal_from_api_key(api_key: str, cfg: Settings) -> Principal:
    """Derive le principal d'une clé API statique (mode démo)."""
    role = cfg.api_key_mapping.get(api_key)
    if role is None:
        raise AuthError("clé API invalide")
    return Principal(
        user_id=f"key:{api_key[:8]}", roles=frozenset({role}), tenant_id=cfg.default_tenant
    )
