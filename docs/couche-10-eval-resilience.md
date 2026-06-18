# Couche 10 — Qualité d'extraction & résilience (M2)

## Sortie JSON contrainte (guided decoding)

L'extraction n'espère plus un JSON « bien formé » : elle **contraint** le VLM via
`guided_json`. Le schéma est dérivé de Pydantic (`extraction_schema()` →
`ExtractedIndicatorDraft.model_json_schema()`, enveloppé en `array`) et transmis dans
`LLMRequest.response_schema`. `OpenAICompatVisionProvider` l'envoie au serveur vLLM
(`guided_json`), qui garantit une sortie conforme (catégories/unités dans l'énumération).
Activable via `EMPREINTE_LLM_GUIDED_DECODING`. Le parsing défensif reste en filet de sécurité.

## Seuil de confiance → revue humaine

Chaque indicateur dont `confidence < EMPREINTE_EXTRACTION_MIN_CONFIDENCE` (défaut 0.5) est
marqué `needs_review=True` (cf. `Extractor._finalize`), pour orienter une validation humaine
avant publication du bilan.

## Circuit breaker

`CircuitBreaker` (dans `gateway.py`) ouvre après `EMPREINTE_CIRCUIT_BREAKER_THRESHOLD` échecs
consécutifs du primaire et **court-circuite** vers le fallback pendant
`EMPREINTE_CIRCUIT_BREAKER_RESET_SEC` (demi-ouverture ensuite). Évite de marteler un vLLM
défaillant. Horloge injectable → tests déterministes. Les timeouts viennent du client httpx
(`EMPREINTE_LLM_TIMEOUT_SEC`).

## Harnais d'évaluation

- `evaluation.py` : `score_extraction(predicted, expected, value_tolerance)` →
  précision/rappel/F1 par catégorie (détection) + `value_accuracy` (exactitude numérique sous
  tolérance relative). Fonctions pures, testées.
- `eval/dataset/*.json` : jeux labellisés (vérité terrain). `eval/run_eval.py` exécute le
  pipeline (démo hors-ligne, ou vrai vLLM si configuré), score, et **sort en erreur sous le
  seuil F1**.
- CI : job `eval` non bloquant (`continue-on-error`) — gate qualité informatif tant que le
  modèle réel n'est pas branché.

> En production, étendre `eval/dataset` avec des documents réels labellisés et resserrer le
> seuil F1 une fois le vLLM mesuré.
