"""Configuration du logging structure (structlog)."""

from __future__ import annotations

import logging

import structlog

from empreinte.config import get_settings


def configure_logging() -> None:
    """Configure structlog en sortie JSON pour l'ensemble de l'application."""
    level = getattr(logging, get_settings().log_level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", level=level)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Retourne un logger structure lie au nom fourni."""
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger
