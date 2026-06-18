# ADR 0002 — Le LLM extrait, le moteur calcule

## Statut

Accepte.

## Contexte

Un bilan carbone doit etre opposable (commissaire aux comptes, auditeur CSRD). Confier le
calcul des emissions a un LLM exposerait a des erreurs arithmetiques et a des hallucinations
chiffrees, non reproductibles et non justifiables.

## Decision

Separer strictement deux responsabilites :

- **Extraction (LLM/VLM)** : lire les documents et restituer des **donnees d'activite**
  (kWh, litres, km) avec leur page source. Le modele n'effectue aucun calcul d'emission.
- **Calcul (moteur deterministe `factors.py`)** : appliquer des facteurs d'emission sourcés
  pour convertir les activites en kg CO2e, par scope.

## Consequences

- **+** Resultats **reproductibles** : memes entrees → memes sorties, independamment du
  modele.
- **+** **Auditabilite** : chaque ligne d'emission cite sa page source et la source du
  facteur ; le calcul est relisible.
- **+** Le risque d'hallucination chiffree est elimine par construction.
- **−** La qualite du bilan depend de l'exhaustivite du catalogue de facteurs ; une categorie
  sans facteur echoue explicitement (`CarbonComputationError`) au lieu de produire un chiffre
  errone.
