"""Observabilite legere : traces de spans et compteurs de metriques en memoire.

Abstrait Langfuse/Prometheus pour rester executable hors-ligne. En production, brancher
``record_span`` sur Langfuse et ``METRICS`` sur un exporter Prometheus.
"""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

from empreinte.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class Span:
    """Trace d'une operation : nom, duree et attributs."""

    name: str
    duration_ms: float
    attributes: dict[str, str]


@dataclass
class Metrics:
    """Compteurs et observations agreges en memoire."""

    counters: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    spans: list[Span] = field(default_factory=list)

    def incr(self, name: str, value: int = 1) -> None:
        """Incremente un compteur nomme."""
        self.counters[name] += value

    def reset(self) -> None:
        """Reinitialise tous les compteurs et spans (utile en tests)."""
        self.counters.clear()
        self.spans.clear()


METRICS = Metrics()


@contextmanager
def record_span(name: str, **attributes: str) -> Iterator[None]:
    """Enregistre la duree d'un bloc et l'ajoute aux spans collectes."""
    start = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        span = Span(name=name, duration_ms=duration_ms, attributes=attributes)
        METRICS.spans.append(span)
        logger.info("span", name=name, duration_ms=round(duration_ms, 2), **attributes)
