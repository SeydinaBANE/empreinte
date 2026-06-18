"""Tests des depots (en memoire et SQL via aiosqlite)."""

from __future__ import annotations

import base64
from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool

from empreinte.object_store import InMemoryObjectStore
from empreinte.repositories import (
    InMemoryDocumentRepository,
    InMemoryReportRepository,
    SqlDocumentRepository,
    SqlReportRepository,
    create_schema,
)
from empreinte.schemas import DocumentPage, FootprintReport, SourceDocument


def _document(doc_id: str = "d1") -> SourceDocument:
    return SourceDocument(
        doc_id=doc_id,
        title="Facture",
        pages=[
            DocumentPage(page_number=1, image_base64=base64.b64encode(b"page-one").decode("ascii"))
        ],
    )


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    eng = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    await create_schema(eng)
    yield eng
    await eng.dispose()


async def test_inmemory_document_seed_and_save() -> None:
    repo = InMemoryDocumentRepository(seed=[_document("seeded")])
    assert await repo.get("seeded") is not None
    await repo.save(_document("d2"))
    assert await repo.get("d2") is not None
    assert await repo.get("missing") is None


async def test_inmemory_report_round_trip() -> None:
    repo = InMemoryReportRepository()
    await repo.save(FootprintReport(doc_id="d1", reporting_year=2025, total_kg_co2e=42.0))
    loaded = await repo.get("d1")
    assert loaded is not None
    assert loaded.total_kg_co2e == 42.0


async def test_sql_document_round_trip(engine: AsyncEngine) -> None:
    repo = SqlDocumentRepository(engine, InMemoryObjectStore())
    await repo.save(_document("d1"))
    loaded = await repo.get("d1")
    assert loaded is not None
    assert loaded.title == "Facture"
    assert base64.b64decode(loaded.pages[0].image_base64) == b"page-one"


async def test_sql_document_get_missing(engine: AsyncEngine) -> None:
    repo = SqlDocumentRepository(engine, InMemoryObjectStore())
    assert await repo.get("ghost") is None


async def test_sql_report_round_trip(engine: AsyncEngine) -> None:
    repo = SqlReportRepository(engine)
    await repo.save(FootprintReport(doc_id="d1", reporting_year=2025, total_kg_co2e=10.5))
    loaded = await repo.get("d1")
    assert loaded is not None
    assert loaded.total_kg_co2e == 10.5
