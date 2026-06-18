"""Gouvernance transverse : RBAC, souverainete des donnees, masquage PII et audit.

Souverainete : en mode souverain, la gateway ne peut viser qu'un endpoint LLM prive
(local), garantissant qu'aucune donnee RSE confidentielle ne quitte l'infrastructure.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from enum import StrEnum
from urllib.parse import urlparse

from empreinte.logging import get_logger
from empreinte.observability import METRICS

logger = get_logger(__name__)

_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_IBAN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b")

_PRIVATE_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_PRIVATE_PREFIXES = ("10.", "192.168.", "172.16.", "172.17.", "172.18.", "172.19.")


class AccessDeniedError(RuntimeError):
    """Action refusee par la politique RBAC."""


class SovereigntyError(RuntimeError):
    """Configuration violant la garantie de souverainete des donnees."""


class Permission(StrEnum):
    """Permissions atomiques exposees par l'application."""

    EXTRACT = "extract"
    REPORT = "report"
    CHAT = "chat"
    ERASE = "erase"


@dataclass(frozen=True)
class Principal:
    """Appelant authentifie : identifiant, roles et tenant."""

    user_id: str
    roles: frozenset[str]
    tenant_id: str = "default"


_ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    "analyst": frozenset({Permission.EXTRACT, Permission.CHAT}),
    "auditor": frozenset(
        {Permission.EXTRACT, Permission.REPORT, Permission.CHAT, Permission.ERASE}
    ),
}


class RBACPolicy:
    """Politique de controle d'acces basee sur les roles."""

    def __init__(self, role_permissions: dict[str, frozenset[Permission]] | None = None) -> None:
        self._role_permissions = role_permissions or _ROLE_PERMISSIONS

    def permissions_of(self, principal: Principal) -> frozenset[Permission]:
        """Union des permissions accordees par les roles du principal."""
        granted: set[Permission] = set()
        for role in principal.roles:
            granted |= self._role_permissions.get(role, frozenset())
        return frozenset(granted)

    def authorize(self, principal: Principal, permission: Permission) -> None:
        """Leve ``AccessDeniedError`` si le principal ne possede pas la permission."""
        if permission not in self.permissions_of(principal):
            METRICS.incr("governance.access_denied")
            raise AccessDeniedError(f"{principal.user_id} non autorise pour {permission}")


def mask_pii(text: str) -> str:
    """Masque emails et IBAN susceptibles d'apparaitre dans des documents fournisseurs."""
    masked = _EMAIL.sub("[email]", text)
    return _IBAN.sub("[iban]", masked)


def assert_sovereign_endpoint(api_base: str, sovereign_mode: bool) -> None:
    """Verifie qu'en mode souverain, l'endpoint LLM reste prive (local)."""
    if not sovereign_mode or not api_base:
        return
    host = urlparse(api_base).hostname or ""
    is_private = (
        host in _PRIVATE_HOSTS
        or host.endswith(".local")
        or "." not in host
        or any(host.startswith(prefix) for prefix in _PRIVATE_PREFIXES)
    )
    if not is_private:
        METRICS.incr("governance.sovereignty_violation")
        raise SovereigntyError(f"endpoint LLM '{host}' externe interdit en mode souverain")


@dataclass(frozen=True)
class AuditEntry:
    """Entree d'audit immuable."""

    user_id: str
    action: str
    resource: str
    allowed: bool
    timestamp: float


@dataclass
class AuditLog:
    """Journal d'audit append-only en memoire."""

    entries: list[AuditEntry] = field(default_factory=list)

    def record(self, principal: Principal, action: str, resource: str, allowed: bool) -> None:
        """Ajoute une entree d'audit et la trace."""
        entry = AuditEntry(
            user_id=principal.user_id,
            action=action,
            resource=resource,
            allowed=allowed,
            timestamp=time.time(),
        )
        self.entries.append(entry)
        logger.info(
            "audit",
            user=principal.user_id,
            action=action,
            resource=resource,
            allowed=allowed,
        )
