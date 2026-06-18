"""Dependances FastAPI injectables (surchargeables en tests)."""

from __future__ import annotations

from fastapi import Header, HTTPException

from empreinte.auth import AuthError, principal_from_api_key, verify_jwt
from empreinte.config import get_settings
from empreinte.governance import AuditLog, Principal, RBACPolicy
from empreinte.services import Pipeline, build_pipeline

_pipeline: Pipeline | None = None


def get_pipeline() -> Pipeline:
    """Retourne le pipeline applicatif (singleton)."""
    global _pipeline
    if _pipeline is None:
        _pipeline = build_pipeline()
    return _pipeline


def get_rbac_policy() -> RBACPolicy:
    """Retourne la politique RBAC (singleton)."""
    return RBACPolicy()


def get_audit_log() -> AuditLog:
    """Retourne le journal d'audit (singleton)."""
    return AuditLog()


def get_principal(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
) -> Principal:
    """Authentifie l'appelant : JWT porteur (mode jwt) ou clé API (mode api_key)."""
    cfg = get_settings()
    if cfg.auth_mode == "jwt":
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="jeton porteur manquant")
        try:
            return verify_jwt(authorization[len("Bearer ") :], cfg)
        except AuthError as exc:
            raise HTTPException(status_code=401, detail="jeton invalide") from exc
    if x_api_key is None:
        raise HTTPException(status_code=401, detail="clé API manquante")
    try:
        return principal_from_api_key(x_api_key, cfg)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail="clé API invalide") from exc
