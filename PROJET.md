# Empreinte — Vision & Architecture

## Le probleme

La directive CSRD impose aux entreprises de declarer des centaines de points de donnee ESG
(norme ESRS). Les donnees source sont **heterogenes et non structurees** : factures
d'energie, releves de consommation, certificats fournisseurs, rapports PDF mêlant tableaux,
graphiques et texte. Les transformer en indicateurs reglementaires se heurte a trois
obstacles :

1. **Multimodalite** — l'information utile est dans des tableaux et des images, pas dans du
   texte propre ; un OCR classique perd la structure.
2. **Confidentialite** — ces documents contiennent des donnees commerciales sensibles qui ne
   peuvent souvent **pas quitter l'infrastructure** de l'entreprise.
3. **Auditabilite** — un chiffre d'emission non tracable, ou « halluciné » par un modele,
   n'est pas opposable devant un commissaire aux comptes.

## La proposition

**Empreinte** transforme ces documents en bilan carbone reglementaire :

1. **ingere** les documents (PDF rendu en images, ou images directes) ;
2. **extrait** les donnees d'activite via un **VLM on-premise** (vision) — chaque donnee
   cite sa page source ;
3. **rattache** chaque donnee a un point de donnee **ESRS** (taxonomie explicite) ;
4. **calcule** les emissions CO2e via un **moteur deterministe** de facteurs d'emission ;
5. **synthetise** un bilan sourcé, et repond aux questions reglementaires via un RAG ESRS.

### Principe directeur : le LLM extrait, le moteur calcule

Le modele ne produit **aucun chiffre d'emission**. Il se limite a lire les pages et a
restituer des donnees d'activite structurees (kWh, litres, km). Le calcul carbone est
effectue par un moteur pur applicant des facteurs d'emission sourcés. Le bilan est donc
**reproductible et auditable**, et le risque d'hallucination chiffree est elimine par
construction.

## Architecture

```
Upload (PDF / image)
        |
   Ingestion (rendu pages-images, base64)
        |
   Extraction multimodale (VLM on-premise) ---> indicateurs d'activite + page source
        |
   Taxonomie ESRS (mapping categorie -> point de donnee E1-5 / E1-6)
        |
   Moteur carbone deterministe (facteurs d'emission -> kg CO2e, par scope)
        |
   Bilan sourcé (FootprintReport)         Assistant reglementaire (RAG ESRS)
        \__________________  ____________________/
                           \/
        Gouvernance transverse : RBAC, souverainete (no egress), masquage PII, audit
        Gateway LLM : primaire + fallback (vLLM/Ollama compatible OpenAI)
```

## Modules (`src/empreinte/`)

| Module | Role |
|---|---|
| `ingestion.py` | Document source → pages-images normalisees (base64) |
| `gateway.py` | Gateway vision : Protocol + provider local deterministe / HTTP, fallback |
| `extraction.py` | Prompt vision, parsing JSON defensif, rattachement ESRS |
| `taxonomy.py` | Mapping explicite categorie d'activite → point de donnee ESRS |
| `factors.py` | Catalogue de facteurs + moteur carbone deterministe |
| `report.py` | Bilan sourcé + narration ancree sur les chiffres calcules |
| `retriever.py` | RAG reglementaire (InMemory demo / Qdrant prod) |
| `assistant.py` | Questions ESRS ancrees sur le corpus |
| `governance.py` | RBAC, souverainete, masquage PII, audit |
| `services.py` | Composition root `build_pipeline()` + `DocumentStore` |
| `api.py` | FastAPI : `/documents`, `/extract`, `/report`, `/chat`, `/health` |

## Choix de portee (MVP)

- Couverture ESRS limitee au **climat** (E1-5 energie, E1-6 GES) — extensible par ajout
  d'entrees de taxonomie et de facteurs.
- Facteurs d'emission : sous-ensemble representatif type Base Carbone ADEME.
- Mode demo entierement hors-ligne (provider deterministe) pour demarrer sans GPU.
