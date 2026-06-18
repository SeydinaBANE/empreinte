# Couche 02 — Extraction multimodale

## Role

A partir des pages-images, faire produire au VLM un tableau JSON de donnees d'activite
environnementales (categorie, valeur, unite, page source, extrait, confiance).

## Modules

`src/empreinte/gateway.py`, `src/empreinte/extraction.py`

## Gateway vision

- `VisionLLMProvider` (Protocol) : contrat minimal `complete` / `stream`.
- `LocalVisionProvider` : deterministe, hors-ligne. Renvoie un JSON canné pour les requetes
  **avec images**, un texte fixe sinon. Sert la demo et les tests.
- `OpenAICompatVisionProvider` : POST `/chat/completions` compatible OpenAI, avec contenu
  multimodal (`image_url` en data-URL base64). Compatible **vLLM** et **Ollama**.
- `LLMGateway` : primaire → fallback automatique sur `LLMProviderError`.

## Prompt

Le system prompt impose : (1) reponse **strictement JSON**, (2) categories et unites dans un
vocabulaire ferme, (3) interdiction d'inventer une valeur (`[]` si rien n'est lisible).

## Parsing defensif

`_isolate_json_array` extrait le premier tableau JSON (tolere les fences markdown). Chaque
element est valide par Pydantic ; un element invalide (categorie/unite inconnue) est
**ignore et compte** (`extraction.rejected`) plutot que de faire echouer tout le document.
Un JSON totalement invalide leve `ExtractionError`.

## Rattachement ESRS

Chaque indicateur extrait passe par `taxonomy.map_indicator` (couche 03) avant d'etre
retourne.
