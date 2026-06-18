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

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from empreinte.logging import get_logger

logger = get_logger(__name__)

_EVENTS = Counter("empreinte_events_total", "Compteur d'evenements applicatifs", ["event"])
_SPAN_DURATION = Histogram("empreinte_span_duration_ms", "Duree des spans (ms)", ["span"])


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
        """Incremente un compteur nomme (en memoire + Prometheus)."""
        self.counters[name] += value
        _EVENTS.labels(event=name).inc(value)

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
        _SPAN_DURATION.labels(span=name).observe(duration_ms)
        logger.info("span", name=name, duration_ms=round(duration_ms, 2), **attributes)


def render_metrics() -> tuple[bytes, str]:
    """Retourne l'exposition Prometheus (payload, content-type)."""
    return generate_latest(), CONTENT_TYPE_LATEST
