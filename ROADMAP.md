# Roadmap

## POC (livré)

- Extraction multimodale deterministe hors-ligne, moteur carbone, API de bout en bout.
- Voir [POC.md](POC.md).

## MVP (livré)

- Pipeline complet (ingestion → extraction → taxonomie → moteur → bilan + RAG), gouvernance,
  souverainete, tests ≥ 80 %, Docker Compose, CI. Voir [MVP.md](MVP.md).

## Au-dela du MVP

- **Couverture ESRS** : etendre au-dela du climat (E1) — eau (E3), dechets (E5), social (S).
- **Facteurs d'emission** : import du referentiel Base Carbone ADEME complet + versioning.
- **Extraction** : consolidation multi-documents, deduplication, niveaux de confiance par
  champ, validation humaine dans la boucle.
- **Export** : generation de rapport CSRD (PDF/XBRL) a partir du `FootprintReport`.
- **Eval** : jeu de documents labellises, precision/rappel d'extraction en CI, faithfulness
  RAG (RAGAS).
- **Production** : indexation du corpus ESRS dans Qdrant, deploiement vLLM sur GPU,
  observabilite Langfuse/Prometheus.
