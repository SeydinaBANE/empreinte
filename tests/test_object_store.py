"""Tests du stockage objet en memoire."""

from __future__ import annotations

import pytest

from empreinte.object_store import InMemoryObjectStore, ObjectStoreError


async def test_put_then_get_round_trip() -> None:
    store = InMemoryObjectStore()
    await store.put("k1", b"payload", content_type="image/png")
    assert await store.get("k1") == b"payload"


async def test_get_missing_raises() -> None:
    store = InMemoryObjectStore()
    with pytest.raises(ObjectStoreError):
        await store.get("absent")
