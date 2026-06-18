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
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from empreinte.object_store import ObjectStore
from empreinte.schemas import DocumentPage, FootprintReport, SourceDocument


class DocumentRepository(Protocol):
    """Persistance des documents source, isolee par tenant."""

    async def save(self, tenant_id: str, document: SourceDocument) -> None:
        """Persiste un document (metadonnees + images de pages) pour un tenant."""
        ...

    async def get(self, tenant_id: str, doc_id: str) -> SourceDocument | None:
        """Recharge un document du tenant ou ``None`` s'il est inconnu/etranger."""
        ...

    async def delete(self, tenant_id: str, doc_id: str) -> None:
        """Supprime un document du tenant (droit a l'effacement)."""
        ...


class ReportRepository(Protocol):
    """Persistance des bilans carbone, isolee par tenant."""

    async def save(self, tenant_id: str, report: FootprintReport) -> None:
        """Persiste un bilan pour un tenant."""
        ...

    async def get(self, tenant_id: str, doc_id: str) -> FootprintReport | None:
        """Recharge le bilan d'un document du tenant ou ``None``."""
        ...

    async def delete(self, tenant_id: str, doc_id: str) -> None:
        """Supprime le bilan d'un document du tenant."""
        ...


class InMemoryDocumentRepository:
    """Depot de documents en memoire (demo/tests), clef par (tenant, doc_id)."""

    def __init__(self, seed: list[tuple[str, SourceDocument]] | None = None) -> None:
        self._documents: dict[tuple[str, str], SourceDocument] = {
            (tenant, doc.doc_id): doc for tenant, doc in seed or []
        }

    async def save(self, tenant_id: str, document: SourceDocument) -> None:
        self._documents[(tenant_id, document.doc_id)] = document

    async def get(self, tenant_id: str, doc_id: str) -> SourceDocument | None:
        return self._documents.get((tenant_id, doc_id))

    async def delete(self, tenant_id: str, doc_id: str) -> None:
        self._documents.pop((tenant_id, doc_id), None)


class InMemoryReportRepository:
    """Depot de bilans en memoire (demo/tests), clef par (tenant, doc_id)."""

    def __init__(self) -> None:
        self._reports: dict[tuple[str, str], FootprintReport] = {}

    async def save(self, tenant_id: str, report: FootprintReport) -> None:
        self._reports[(tenant_id, report.doc_id)] = report

    async def get(self, tenant_id: str, doc_id: str) -> FootprintReport | None:
        return self._reports.get((tenant_id, doc_id))

    async def delete(self, tenant_id: str, doc_id: str) -> None:
        self._reports.pop((tenant_id, doc_id), None)


class Base(DeclarativeBase):
    """Base declarative des modeles SQL."""


class DocumentRow(Base):
    __tablename__ = "documents"

    doc_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )


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
    tenant_id: Mapped[str] = mapped_column(String(128), index=True)
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

    def _page_key(self, tenant_id: str, doc_id: str, page_number: int) -> str:
        return f"{self._prefix}/{tenant_id}/{doc_id}/p{page_number}.bin"

    async def save(self, tenant_id: str, document: SourceDocument) -> None:
        async with self._sessionmaker.begin() as session:
            await session.merge(
                DocumentRow(doc_id=document.doc_id, tenant_id=tenant_id, title=document.title)
            )
            for page in document.pages:
                key = self._page_key(tenant_id, document.doc_id, page.page_number)
                await self._store.put(key, base64.b64decode(page.image_base64), page.media_type)
                session.add(
                    DocumentPageRow(
                        doc_id=document.doc_id,
                        page_number=page.page_number,
                        object_key=key,
                        media_type=page.media_type,
                    )
                )

    async def get(self, tenant_id: str, doc_id: str) -> SourceDocument | None:
        async with self._sessionmaker() as session:
            row = await session.get(DocumentRow, doc_id)
            if row is None or row.tenant_id != tenant_id:
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

    async def delete(self, tenant_id: str, doc_id: str) -> None:
        async with self._sessionmaker.begin() as session:
            row = await session.get(DocumentRow, doc_id)
            if row is None or row.tenant_id != tenant_id:
                return
            await self._delete_with_pages(session, row)

    async def purge_older_than(self, cutoff: datetime) -> int:
        """Supprime (tous tenants) les documents anterieurs a ``cutoff`` (retention RGPD)."""
        async with self._sessionmaker.begin() as session:
            rows = (
                await session.scalars(select(DocumentRow).where(DocumentRow.created_at < cutoff))
            ).all()
            for row in rows:
                await self._delete_with_pages(session, row)
        return len(rows)

    async def _delete_with_pages(self, session: AsyncSession, row: DocumentRow) -> None:
        page_rows = (
            await session.scalars(
                select(DocumentPageRow).where(DocumentPageRow.doc_id == row.doc_id)
            )
        ).all()
        for page_row in page_rows:
            await self._store.delete(page_row.object_key)
            await session.delete(page_row)
        await session.delete(row)


class SqlReportRepository:
    """Depot de bilans : serialisation JSON du ``FootprintReport`` en SQL."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async def save(self, tenant_id: str, report: FootprintReport) -> None:
        async with self._sessionmaker.begin() as session:
            await session.merge(
                ReportRow(
                    doc_id=report.doc_id, tenant_id=tenant_id, payload=report.model_dump_json()
                )
            )

    async def get(self, tenant_id: str, doc_id: str) -> FootprintReport | None:
        async with self._sessionmaker() as session:
            row = await session.get(ReportRow, doc_id)
        if row is None or row.tenant_id != tenant_id:
            return None
        return FootprintReport.model_validate_json(row.payload)

    async def delete(self, tenant_id: str, doc_id: str) -> None:
        async with self._sessionmaker.begin() as session:
            row = await session.get(ReportRow, doc_id)
            if row is not None and row.tenant_id == tenant_id:
                await session.delete(row)
