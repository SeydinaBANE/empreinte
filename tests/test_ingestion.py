"""Tests de l'ingestion documentaire (images -> pages normalisees)."""

from __future__ import annotations

import base64

import pytest

from empreinte.ingestion import (
    IngestionError,
    document_from_images,
    encode_image,
    page_from_bytes,
)


def test_page_from_bytes_encodes_base64() -> None:
    page = page_from_bytes(page_number=2, image_bytes=b"hello")
    assert page.page_number == 2
    assert base64.b64decode(page.image_base64) == b"hello"


def test_encode_image_defaults_to_page_one() -> None:
    assert encode_image(b"x").page_number == 1


def test_page_from_bytes_rejects_empty() -> None:
    with pytest.raises(IngestionError):
        page_from_bytes(page_number=1, image_bytes=b"")


def test_document_from_images_numbers_pages() -> None:
    document = document_from_images("d1", "Doc", [b"a", b"b", b"c"])
    assert document.page_count == 3
    assert [p.page_number for p in document.pages] == [1, 2, 3]


def test_document_from_images_rejects_empty_list() -> None:
    with pytest.raises(IngestionError):
        document_from_images("d1", "Doc", [])
