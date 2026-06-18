# Couche 03 — Taxonomie ESRS

## Role

Rattacher chaque categorie d'activite a un point de donnee ESRS, de maniere **explicite et
versionnable** — pas par decision du LLM.

## Module

`src/empreinte/taxonomy.py`

## Mapping

| Categorie d'activite | Point de donnee ESRS |
|---|---|
| `electricity`, `natural_gas`, `district_heating` | **E1-5** — Consommation et mix energetiques |
| `diesel`, `petrol`, `business_travel_car`, `waste` | **E1-6** — Emissions brutes de GES |

Toute categorie non cartographiee retombe sur `EsrsDatapoint.UNMAPPED`.

## Pourquoi un mapping explicite

- **Auditabilite** : le rattachement reglementaire est une regle metier, pas une sortie
  probabiliste. Il doit etre relisible et justifiable.
- **Extensibilite** : ajouter un point de donnee ESRS = ajouter une entree dans
  `_CATEGORY_TO_DATAPOINT` (+ un facteur dans la couche 04).

## API

- `datapoint_for(category)` → point de donnee
- `label_of(datapoint)` → libelle humain
- `map_indicator(indicator)` → copie de l'indicateur avec `datapoint` renseigne
