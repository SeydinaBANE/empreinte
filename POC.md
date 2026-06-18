# POC — Preuve de concept

## Objectif

Demontrer qu'un VLM peut extraire des donnees d'activite d'un document et qu'un moteur
deterministe en derive un bilan carbone sourcé, le tout hors-ligne.

## Perimetre

- Gateway vision avec provider local deterministe (JSON canné).
- Moteur carbone : 7 categories d'activite, 3 scopes, conversions d'unites.
- Mapping ESRS explicite (E1-5, E1-6).
- API minimale : `/extract`, `/report`, `/health`.

## Critere de succes

`POST /report` sur le document de demo renvoie un bilan CO2e ventile par scope, chaque ligne
citant sa page source et la source du facteur — sans aucun service externe.

## Resultat

Atteint. Valide par `test_api.py::test_auditor_generates_report` et
`test_services.py::test_demo_pipeline_extracts_canned_indicators`.
