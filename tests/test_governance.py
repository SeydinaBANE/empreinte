"""Tests de la gouvernance : RBAC, souverainete, masquage PII."""

from __future__ import annotations

import pytest

from empreinte.governance import (
    AccessDeniedError,
    AuditLog,
    Permission,
    Principal,
    RBACPolicy,
    SovereigntyError,
    assert_sovereign_endpoint,
    mask_pii,
)


def _principal(role: str) -> Principal:
    return Principal(user_id="u", roles=frozenset({role}))


def test_auditor_can_report() -> None:
    RBACPolicy().authorize(_principal("auditor"), Permission.REPORT)


def test_analyst_cannot_report() -> None:
    with pytest.raises(AccessDeniedError):
        RBACPolicy().authorize(_principal("analyst"), Permission.REPORT)


def test_mask_pii_masks_email_and_iban() -> None:
    masked = mask_pii("contact ops@acme.example IBAN FR7630006000011234567890189")
    assert "ops@acme.example" not in masked
    assert "[email]" in masked
    assert "[iban]" in masked


def test_sovereign_endpoint_allows_localhost() -> None:
    assert_sovereign_endpoint("http://localhost:8001/v1", sovereign_mode=True)


def test_sovereign_endpoint_rejects_external_host() -> None:
    with pytest.raises(SovereigntyError):
        assert_sovereign_endpoint("https://api.openai.com/v1", sovereign_mode=True)


def test_sovereign_endpoint_noop_when_disabled() -> None:
    assert_sovereign_endpoint("https://api.openai.com/v1", sovereign_mode=False)


def test_audit_log_records_entry() -> None:
    log = AuditLog()
    log.record(_principal("analyst"), action="extract", resource="doc", allowed=True)
    assert log.entries[0].action == "extract"
    assert log.entries[0].allowed is True
