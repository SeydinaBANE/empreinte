# Couche 05 — RAG reglementaire & assistant

## Role

Repondre aux questions reglementaires (ESRS/CSRD) en s'ancrant sur un corpus, sans
hallucination, avec citation des passages.

## Modules

`src/empreinte/retriever.py`, `src/empreinte/assistant.py`

## Retriever

- `Retriever` (Protocol) : `retrieve(query, top_k) -> list[RetrievedPassage]`.
- `InMemoryRetriever` : scoring lexical par recouvrement de tokens, sans dependance externe
  (mode demo + tests). Une requete vide ne retourne rien.
- `QdrantRetriever` : recherche vectorielle en production (`EMPREINTE_QDRANT_URL`).

## Assistant

`RegulatoryAssistant` : retrouve les passages pertinents, construit un prompt qui borne la
reponse aux passages fournis, puis synthetise via la gateway. En l'absence de reponse du
modele, il **retombe sur le passage le plus pertinent** plutot que de renvoyer du vide.
`answer_stream` diffuse la reponse en SSE.

## Corpus de demo

Trois passages ESRS (E1-5, E1-6, scopes GHG) sont seedés dans `services.py`. En production,
le corpus reglementaire complet est indexe dans Qdrant.
