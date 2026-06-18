"""Construction du bilan carbone : calcul deterministe puis narration ancree.

Les chiffres proviennent exclusivement du moteur deterministe. Le LLM ne sert qu'a
rediger une synthese a partir de ces chiffres deja calcules ; en l'absence de reponse
exploitable, on retombe sur la synthese factuelle generee localement.
"""

from __future__ import annotations

from empreinte.factors import CarbonEngine, aggregate_by_scope
from empreinte.gateway import LLMGateway
from empreinte.schemas import (
    EmissionLine,
    EmissionScope,
    ExtractionResult,
    FootprintReport,
    LLMRequest,
    Message,
    Role,
)

_SCOPE_LABELS: dict[EmissionScope, str] = {
    EmissionScope.SCOPE_1: "Scope 1 (emissions directes)",
    EmissionScope.SCOPE_2: "Scope 2 (energie achetee)",
    EmissionScope.SCOPE_3: "Scope 3 (autres emissions indirectes)",
}

_NARRATIVE_SYSTEM = (
    "Tu rediges une synthese de bilan carbone en francais, en 2 a 3 phrases. Utilise "
    "EXCLUSIVEMENT les chiffres fournis, n'en invente aucun et n'en recalcule aucun."
)


class ReportBuilder:
    """Assemble un ``FootprintReport`` sourcé a partir d'une extraction."""

    def __init__(self, engine: CarbonEngine, gateway: LLMGateway, reporting_year: int) -> None:
        self._engine = engine
        self._gateway = gateway
        self._reporting_year = reporting_year

    async def build(self, extraction: ExtractionResult) -> FootprintReport:
        """Calcule le bilan puis y joint une narration ancree sur les chiffres."""
        lines = self._engine.compute(extraction.indicators)
        by_scope = aggregate_by_scope(lines)
        total = round(sum(by_scope.values()), 3)
        facts = self._facts(lines, by_scope, total)
        narrative = await self._narrate(facts)
        return FootprintReport(
            doc_id=extraction.doc_id,
            reporting_year=self._reporting_year,
            lines=lines,
            total_kg_co2e=total,
            by_scope_kg_co2e=by_scope,
            narrative=narrative,
        )

    def _facts(
        self, lines: list[EmissionLine], by_scope: dict[EmissionScope, float], total: float
    ) -> str:
        parts = [f"Bilan {self._reporting_year} : total {total} kg CO2e sur {len(lines)} poste(s)."]
        for scope in (EmissionScope.SCOPE_1, EmissionScope.SCOPE_2, EmissionScope.SCOPE_3):
            if scope in by_scope:
                parts.append(f"{_SCOPE_LABELS[scope]} : {by_scope[scope]} kg CO2e.")
        return " ".join(parts)

    async def _narrate(self, facts: str) -> str:
        request = LLMRequest(
            messages=[
                Message(role=Role.SYSTEM, content=_NARRATIVE_SYSTEM),
                Message(role=Role.USER, content=facts),
            ]
        )
        response = await self._gateway.complete(request)
        return response.content.strip() or facts
