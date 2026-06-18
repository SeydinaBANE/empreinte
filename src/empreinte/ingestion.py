"""Ingestion documentaire : transforme un fichier source en pages-images normalisees.

Le coeur est une fonction pure operant sur des octets d'image (testable hors-ligne) ;
le rendu PDF -> images via ``pypdfium2`` est une fine enveloppe optionnelle (extra ``pdf``).
"""

from __future__ import annotations

import base64

from empreinte.observability import record_span
from empreinte.schemas import DocumentPage, SourceDocument

_PNG = "image/png"


class IngestionError(RuntimeError):
    """Echec de transformation d'un document en pages-images."""


def encode_image(image_bytes: bytes, media_type: str = _PNG) -> DocumentPage:
    """Encode des octets d'image en page (placeholder de numero de page a 1)."""
    return page_from_bytes(page_number=1, image_bytes=image_bytes, media_type=media_type)


def page_from_bytes(page_number: int, image_bytes: bytes, media_type: str = _PNG) -> DocumentPage:
    """Construit une ``DocumentPage`` a partir d'octets d'image."""
    if not image_bytes:
        raise IngestionError("image vide")
    return DocumentPage(
        page_number=page_number,
        image_base64=base64.b64encode(image_bytes).decode("ascii"),
        media_type=media_type,
    )


def document_from_images(
    doc_id: str, title: str, images: list[bytes], media_type: str = _PNG
) -> SourceDocument:
    """Assemble un document a partir d'une liste d'images (une par page)."""
    if not images:
        raise IngestionError("aucune page fournie")
    pages = [
        page_from_bytes(page_number=index, image_bytes=data, media_type=media_type)
        for index, data in enumerate(images, start=1)
    ]
    return SourceDocument(doc_id=doc_id, title=title, pages=pages)


def render_pdf(doc_id: str, title: str, pdf_bytes: bytes, dpi: int = 150) -> SourceDocument:
    """Rend chaque page d'un PDF en image PNG (necessite l'extra ``pdf``)."""
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:  # pragma: no cover - depend de l'extra optionnel
        raise IngestionError("pypdfium2 requis pour le rendu PDF (extra 'pdf')") from exc

    with record_span("ingestion.render_pdf", doc_id=doc_id):
        pdf = pdfium.PdfDocument(pdf_bytes)
        scale = dpi / 72.0
        images: list[bytes] = []
        try:
            for index in range(len(pdf)):
                bitmap = pdf[index].render(scale=scale)
                images.append(_bitmap_to_png(bitmap))
        finally:
            pdf.close()
    return document_from_images(doc_id=doc_id, title=title, images=images)


def _bitmap_to_png(bitmap: object) -> bytes:  # pragma: no cover - depend de l'extra optionnel
    """Convertit un bitmap pypdfium2 en octets PNG."""
    import io

    pil_image = bitmap.to_pil()  # type: ignore[attr-defined]
    buffer = io.BytesIO()
    pil_image.save(buffer, format="PNG")
    return buffer.getvalue()
