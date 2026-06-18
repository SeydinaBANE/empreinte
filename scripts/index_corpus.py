"""Indexe le corpus reglementaire ESRS dans Qdrant (embeddings fastembed locaux).

Usage :
    EMPREINTE_QDRANT_URL=http://localhost:6333 python scripts/index_corpus.py

L'embedding tourne en local (fastembed), sans appel externe — coherent avec la souverainete.
En production, etendre ``empreinte.corpus.ESRS_CORPUS`` au texte ESRS/CSRD complet (chunke).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from empreinte.config import get_settings  # noqa: E402
from empreinte.corpus import ESRS_CORPUS  # noqa: E402
from empreinte.logging import configure_logging, get_logger  # noqa: E402

logger = get_logger(__name__)


async def index_corpus() -> int:
    """Cree/peuple la collection Qdrant a partir du corpus ESRS. Retourne le nombre de docs."""
    from qdrant_client import AsyncQdrantClient

    cfg = get_settings()
    if not cfg.qdrant_url:
        raise SystemExit("EMPREINTE_QDRANT_URL est requis pour l'indexation")

    client = AsyncQdrantClient(url=cfg.qdrant_url)
    try:
        await client.add(
            collection_name=cfg.qdrant_collection,
            documents=[doc.text for doc in ESRS_CORPUS],
            metadata=[{"datapoint": doc.datapoint.value} for doc in ESRS_CORPUS],
            ids=list(range(1, len(ESRS_CORPUS) + 1)),
        )
    finally:
        await client.close()

    logger.info("corpus_indexed", collection=cfg.qdrant_collection, count=len(ESRS_CORPUS))
    return len(ESRS_CORPUS)


def main() -> None:
    configure_logging()
    count = asyncio.run(index_corpus())
    logger.info("done", indexed=count)


if __name__ == "__main__":
    main()
