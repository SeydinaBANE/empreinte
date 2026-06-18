"""Tests d'integration de l'API en mode demo (hors-ligne)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from empreinte.api import app

_ANALYST = {"X-API-Key": "dev-key-analyst"}
_AUDITOR = {"X-API-Key": "dev-key-auditor"}
_DEMO_DOC = "demo-facture-energie"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_is_public(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_chat_requires_api_key_header(client: TestClient) -> None:
    assert client.post("/chat", json={"question": "scope 2 ?"}).status_code == 422


def test_invalid_api_key_is_rejected(client: TestClient) -> None:
    response = client.post("/chat", json={"question": "q"}, headers={"X-API-Key": "nope"})
    assert response.status_code == 401


def test_extract_demo_document(client: TestClient) -> None:
    response = client.post("/extract", json={"document_id": _DEMO_DOC}, headers=_ANALYST)
    assert response.status_code == 200
    assert len(response.json()["indicators"]) == 4


def test_extract_unknown_document_404(client: TestClient) -> None:
    response = client.post("/extract", json={"document_id": "ghost"}, headers=_ANALYST)
    assert response.status_code == 404


def test_analyst_cannot_generate_report(client: TestClient) -> None:
    response = client.post("/report", json={"document_id": _DEMO_DOC}, headers=_ANALYST)
    assert response.status_code == 403


def test_auditor_generates_report(client: TestClient) -> None:
    response = client.post("/report", json={"document_id": _DEMO_DOC}, headers=_AUDITOR)
    assert response.status_code == 200
    body = response.json()
    assert body["total_kg_co2e"] > 0
    assert body["lines"]


def test_chat_returns_answer(client: TestClient) -> None:
    response = client.post("/chat", json={"question": "Que couvre le scope 2 ?"}, headers=_AUDITOR)
    assert response.status_code == 200
    assert "passages" in response.json()


def test_upload_then_extract(client: TestClient) -> None:
    upload = client.post(
        "/documents",
        headers=_ANALYST,
        files={"file": ("facture.png", b"fake-image-bytes", "image/png")},
    )
    assert upload.status_code == 200
    doc_id = upload.json()["doc_id"]
    extract = client.post("/extract", json={"document_id": doc_id}, headers=_ANALYST)
    assert extract.status_code == 200
