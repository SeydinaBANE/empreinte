# Couche 04 — Moteur carbone deterministe

## Role

Convertir les donnees d'activite en emissions kg CO2e, par scope GHG Protocol, de maniere
**pure et reproductible**. C'est ici qu'est calcule le bilan — jamais par le LLM.

## Module

`src/empreinte/factors.py`

## Catalogue de facteurs

Sous-ensemble representatif (type Base Carbone ADEME), indexe par categorie :

| Categorie | Unite | kg CO2e / unite | Scope |
|---|---|---|---|
| electricity | kWh | 0.0599 | 2 |
| natural_gas | kWh | 0.227 | 1 |
| district_heating | kWh | 0.116 | 2 |
| diesel | L | 2.51 | 1 |
| petrol | L | 2.28 | 1 |
| business_travel_car | km | 0.193 | 3 |
| waste | kg | 0.467 | 3 |

## Calcul

1. `CarbonEngine.compute_line` recupere le facteur de la categorie.
2. La valeur d'activite est convertie vers l'unite canonique du facteur (`MWh→kWh`,
   `t→kg`) ; une conversion impossible leve `CarbonComputationError`.
3. `kg_co2e = valeur_canonique × facteur`, arrondi a 3 decimales.
4. La ligne conserve la **page source** et la **source du facteur** (tracabilite).

`aggregate_by_scope` consolide les emissions par scope.

## Garanties

- Determinisme total : memes entrees → memes sorties.
- Aucune estimation confiee au modele → pas d'hallucination chiffree possible.
- Une categorie sans facteur echoue explicitement plutot que de produire un faux zero.
