# ADR 0001 — VLM multimodal on-premise plutot qu'API cloud + OCR

## Statut

Accepte.

## Contexte

Les donnees source ESG sont multimodales (tableaux, graphiques, scans) et confidentielles.
Deux axes de decision : (1) comment lire les documents, (2) ou tourne le modele.

## Decision

1. **Modele vision (VLM)** plutot que pipeline OCR + post-traitement : le VLM lit
   directement la mise en page (tableaux, libelles) et restitue des donnees structurees,
   robuste aux formats heterogenes.
2. **On-premise** via un serveur compatible OpenAI (**vLLM** ou **Ollama**) servant un VLM
   open-source (Qwen2.5-VL, Llama-3.2-Vision), jamais une API cloud proprietaire.

## Consequences

- **+** Souverainete : les documents ne quittent pas l'infrastructure (cf. ADR souverainete,
  `assert_sovereign_endpoint`).
- **+** Pas de cout par token ni de dependance fournisseur ; modeles interchangeables via une
  interface compatible OpenAI.
- **+** L'abstraction `VisionLLMProvider` permet de basculer en mode demo deterministe
  hors-ligne (sans GPU) pour les tests et la prise en main.
- **−** Necessite une infrastructure GPU en production ; la qualite depend du VLM open-source
  retenu. Mitige par le fallback de la gateway et le mode demo.
