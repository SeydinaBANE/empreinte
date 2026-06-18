"""Purge de retention RGPD : supprime les documents au-dela de la duree de conservation.

Usage (a planifier en CronJob) :
    EMPREINTE_SQL_DSN=... EMPREINTE_OBJECT_STORE_ENDPOINT=... python scripts/purge_retention.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from empreinte.config import get_settings  # noqa: E402
from empreinte.logging import configure_logging, get_logger  # noqa: E402
from empreinte.repositories import SqlDocumentRepository  # noqa: E402
from empreinte.services import _build_object_store  # noqa: E402

logger = get_logger(__name__)


async def purge() -> int:
    from sqlalchemy.ext.asyncio import create_async_engine

    cfg = get_settings()
    if not cfg.sql_dsn:
        raise SystemExit("EMPREINTE_SQL_DSN est requis pour la purge de retention")
    engine = create_async_engine(cfg.sql_dsn, pool_pre_ping=True)
    repo = SqlDocumentRepository(engine, _build_object_store(cfg))
    cutoff = (datetime.now(UTC) - timedelta(days=cfg.retention_days)).replace(tzinfo=None)
    try:
        purged = await repo.purge_older_than(cutoff)
    finally:
        await engine.dispose()
    logger.info("retention_purge", purged=purged, retention_days=cfg.retention_days)
    return purged


def main() -> None:
    configure_logging()
    asyncio.run(purge())


if __name__ == "__main__":
    main()
