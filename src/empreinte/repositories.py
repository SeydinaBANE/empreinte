"""Persistance des documents et des bilans.

Abstraite par Protocol : implementations en memoire (demo/tests) et SQL (Postgres en prod).
Les metadonnees vont en base ; les images de pages vont dans le stockage objet
(``ObjectStore``), seules leurs cles etant persistees en base.
"""

from __future__ import annotations

import base64
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import ForeignKey, String, Text, select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from empreinte.object_store import ObjectStore
from empreinte.schemas import DocumentPage, FootprintReport, SourceDocument


class DocumentRepository(Protocol):
    """Persistance des documents source."""

    async def save(self, document: SourceDocument) -> None:
        """Persiste un document (metadonnees + images de pages)."""
        ...

    async def get(self, doc_id: str) -> SourceDocument | None:
        """Recharge un document complet ou ``None`` s'il est inconnu."""
        ...


class ReportRepository(Protocol):
    """Persistance des bilans carbone."""

    async def save(self, report: FootprintReport) -> None:
        """Persiste un bilan."""
        ...

    async def get(self, doc_id: str) -> FootprintReport | None:
        """Recharge le bilan d'un document ou ``None``."""
        ...


class InMemoryDocumentRepository:
    """Depot de documents en memoire (demo/tests)."""

    def __init__(self, seed: list[SourceDocument] | None = None) -> None:
        self._documents: dict[str, SourceDocument] = {doc.doc_id: doc for doc in seed or []}

    async def save(self, document: SourceDocument) -> None:
        self._documents[document.doc_id] = document

    async def get(self, doc_id: str) -> SourceDocument | None:
        return self._documents.get(doc_id)


class InMemoryReportRepository:
    """Depot de bilans en memoire (demo/tests)."""

    def __init__(self) -> None:
        self._reports: dict[str, FootprintReport] = {}

    async def save(self, report: FootprintReport) -> None:
        self._reports[report.doc_id] = report

    async def get(self, doc_id: str) -> FootprintReport | None:
        return self._reports.get(doc_id)


class Base(DeclarativeBase):
    """Base declarative des modeles SQL."""


class DocumentRow(Base):
    __tablename__ = "documents"

    doc_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    title: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))


class DocumentPageRow(Base):
    __tablename__ = "document_pages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    doc_id: Mapped[str] = mapped_column(ForeignKey("documents.doc_id"), index=True)
    page_number: Mapped[int] = mapped_column()
    object_key: Mapped[str] = mapped_column(String(1024))
    media_type: Mapped[str] = mapped_column(String(128))


class ReportRow(Base):
    __tablename__ = "reports"

    doc_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    payload: Mapped[str] = mapped_column(Text)


async def create_schema(engine: AsyncEngine) -> None:
    """Cree les tables (dev/tests ; en production : migrations Alembic)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class SqlDocumentRepository:
    """Depot de documents : metadonnees en SQL, images dans le stockage objet."""

    def __init__(
        self, engine: AsyncEngine, object_store: ObjectStore, key_prefix: str = "documents"
    ) -> None:
        self._sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
        self._store = object_store
        self._prefix = key_prefix

    def _page_key(self, doc_id: str, page_number: int) -> str:
        return f"{self._prefix}/{doc_id}/p{page_number}.bin"

    async def save(self, document: SourceDocument) -> None:
        async with self._sessionmaker.begin() as session:
            await session.merge(DocumentRow(doc_id=document.doc_id, title=document.title))
            for page in document.pages:
                key = self._page_key(document.doc_id, page.page_number)
                await self._store.put(key, base64.b64decode(page.image_base64), page.media_type)
                session.add(
                    DocumentPageRow(
                        doc_id=document.doc_id,
                        page_number=page.page_number,
                        object_key=key,
                        media_type=page.media_type,
                    )
                )

    async def get(self, doc_id: str) -> SourceDocument | None:
        async with self._sessionmaker() as session:
            row = await session.get(DocumentRow, doc_id)
            if row is None:
                return None
            page_rows = (
                await session.scalars(
                    select(DocumentPageRow)
                    .where(DocumentPageRow.doc_id == doc_id)
                    .order_by(DocumentPageRow.page_number)
                )
            ).all()
        pages: list[DocumentPage] = []
        for page_row in page_rows:
            data = await self._store.get(page_row.object_key)
            pages.append(
                DocumentPage(
                    page_number=page_row.page_number,
                    image_base64=base64.b64encode(data).decode("ascii"),
                    media_type=page_row.media_type,
                )
            )
        return SourceDocument(doc_id=row.doc_id, title=row.title, pages=pages)


class SqlReportRepository:
    """Depot de bilans : serialisation JSON du ``FootprintReport`` en SQL."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async def save(self, report: FootprintReport) -> None:
        async with self._sessionmaker.begin() as session:
            await session.merge(ReportRow(doc_id=report.doc_id, payload=report.model_dump_json()))

    async def get(self, doc_id: str) -> FootprintReport | None:
        async with self._sessionmaker() as session:
            row = await session.get(ReportRow, doc_id)
        if row is None:
            return None
        return FootprintReport.model_validate_json(row.payload)
