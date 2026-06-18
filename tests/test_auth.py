"""Tests d'authentification : JWT (HS256) et clé API."""

from __future__ import annotations

import jwt
import pytest

from empreinte.auth import AuthError, principal_from_api_key, verify_jwt
from empreinte.config import Settings


def _jwt_settings() -> Settings:
    return Settings(
        auth_mode="jwt",
        jwt_algorithm="HS256",
        jwt_secret="test-secret",
        jwt_issuer="https://idp.example",
        jwt_audience="empreinte",
    )


def _token(secret: str = "test-secret", **claims: object) -> str:
    payload: dict[str, object] = {
        "sub": "user-1",
        "iss": "https://idp.example",
        "aud": "empreinte",
        "roles": ["auditor"],
        "tenant_id": "acme",
    }
    payload.update(claims)
    return jwt.encode(payload, secret, algorithm="HS256")


def test_verify_jwt_extracts_roles_and_tenant() -> None:
    principal = verify_jwt(_token(), _jwt_settings())
    assert principal.user_id == "user-1"
    assert "auditor" in principal.roles
    assert principal.tenant_id == "acme"


def test_verify_jwt_roles_as_space_separated_string() -> None:
    principal = verify_jwt(_token(roles="analyst auditor"), _jwt_settings())
    assert principal.roles == frozenset({"analyst", "auditor"})


def test_verify_jwt_rejects_bad_signature() -> None:
    with pytest.raises(AuthError):
        verify_jwt(_token(secret="wrong-secret"), _jwt_settings())


def test_verify_jwt_rejects_wrong_audience() -> None:
    with pytest.raises(AuthError):
        verify_jwt(_token(aud="other"), _jwt_settings())


def test_verify_jwt_defaults_tenant_when_absent() -> None:
    token = jwt.encode(
        {"sub": "u", "iss": "https://idp.example", "aud": "empreinte", "roles": ["analyst"]},
        "test-secret",
        algorithm="HS256",
    )
    assert verify_jwt(token, _jwt_settings()).tenant_id == "demo"


def test_principal_from_api_key_maps_role_and_tenant() -> None:
    principal = principal_from_api_key("dev-key-auditor", Settings())
    assert "auditor" in principal.roles
    assert principal.tenant_id == "demo"


def test_principal_from_api_key_rejects_unknown() -> None:
    with pytest.raises(AuthError):
        principal_from_api_key("nope", Settings())
