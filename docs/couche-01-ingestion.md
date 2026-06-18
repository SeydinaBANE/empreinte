# Couche 01 — Ingestion documentaire

## Role

Transformer un fichier source heterogene (PDF multi-pages ou image) en une liste de pages
normalisees, encodees en base64, pretes pour l'extraction vision.

## Module

`src/empreinte/ingestion.py`

## Conception

- Le coeur (`page_from_bytes`, `document_from_images`) est **pur** : il opere sur des octets
  d'image, sans dependance externe — donc testable hors-ligne.
- Le rendu PDF → images (`render_pdf`) est une fine enveloppe optionnelle reposant sur
  `pypdfium2` (extra `pdf`). L'import est tardif et garde : en son absence, une
  `IngestionError` explicite est levee.
- Chaque page porte son `page_number` (1-based), ce qui permet de **tracer la source** des
  indicateurs extraits jusqu'a la page d'origine.

## Erreurs

| Cas | Comportement |
|---|---|
| Image vide | `IngestionError("image vide")` |
| Liste de pages vide | `IngestionError("aucune page fournie")` |
| `pypdfium2` absent | `IngestionError` (extra `pdf` requis) |

## DPI de rendu

Configurable via `EMPREINTE_PDF_RENDER_DPI` (defaut 150) — compromis lisibilite/taille pour
le VLM.
