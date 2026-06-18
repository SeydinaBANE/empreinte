"""Corpus reglementaire ESRS de demarrage (seed du RAG).

Sert de fixture pour l'``InMemoryRetriever`` (demo) et de jeu initial pour l'indexation
Qdrant (``scripts/index_corpus.py``). En production, ce corpus est etendu au texte ESRS/CSRD
complet, chunke et indexe.
"""

from __future__ import annotations

from empreinte.retriever import RegulatoryDoc
from empreinte.schemas import EsrsDatapoint

ESRS_CORPUS: list[RegulatoryDoc] = [
    RegulatoryDoc(
        doc_id="esrs-e1-5",
        datapoint=EsrsDatapoint.E1_5_ENERGY,
        text=(
            "ESRS E1-5 impose de declarer la consommation energetique totale en MWh, ventilee "
            "par sources renouvelables et non renouvelables, ainsi que le mix energetique."
        ),
    ),
    RegulatoryDoc(
        doc_id="esrs-e1-6",
        datapoint=EsrsDatapoint.E1_6_GHG,
        text=(
            "ESRS E1-6 impose de declarer les emissions brutes de gaz a effet de serre des "
            "scopes 1, 2 et 3 en tonnes equivalent CO2, et les emissions totales consolidees."
        ),
    ),
    RegulatoryDoc(
        doc_id="ghg-scopes",
        datapoint=EsrsDatapoint.E1_6_GHG,
        text=(
            "Le scope 2 couvre les emissions indirectes liees a l'energie achetee et consommee "
            "(electricite, chaleur, vapeur). Le scope 1 couvre les emissions directes."
        ),
    ),
]
