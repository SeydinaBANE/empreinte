# ADR 0003 — Mapping ESRS explicite plutot que classification par LLM

## Statut

Accepte.

## Contexte

Chaque donnee d'activite doit etre rattachee a un point de donnee ESRS. On pourrait demander
au LLM de classer directement, mais le rattachement reglementaire est une **regle metier**
qui doit etre stable, relisible et justifiable.

## Decision

Maintenir un mapping explicite `categorie d'activite → point de donnee ESRS` dans
`taxonomy.py` (`_CATEGORY_TO_DATAPOINT`), applique apres l'extraction. Le LLM ne fait que
classer la donnee dans un vocabulaire ferme de categories ; la correspondance reglementaire
est deterministe.

## Consequences

- **+** Rattachement **stable et auditable**, independant de la version du modele.
- **+** Extensible : couvrir un nouveau point de donnee ESRS = ajouter une entree (+ un
  facteur d'emission cote couche 04).
- **+** Testable trivialement (`test_taxonomy.py`).
- **−** Le vocabulaire de categories doit etre maintenu et aligne avec le prompt
  d'extraction ; une categorie hors vocabulaire retombe sur `UNMAPPED`.
