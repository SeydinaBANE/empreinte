"""Dependances FastAPI injectables (surchargeables en tests)."""

from __future__ import annotations

from fastapi import Header, HTTPException

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
    x_api_key: str = Header(..., description="API key for authentication"),
) -> Principal:
    """Extrait le principal authentifie depuis le header ``X-API-Key``."""
    settings = get_settings()
    role = settings.api_key_mapping.get(x_api_key)
    if role is None:
        raise HTTPException(status_code=401, detail="invalid API key")
    return Principal(user_id=f"key:{x_api_key[:8]}", roles=frozenset({role}))
