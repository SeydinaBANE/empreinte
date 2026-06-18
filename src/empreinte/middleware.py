"""Middleware applicatif : rate limiting, correlation ID."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from collections.abc import Awaitable, Callable

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from empreinte.logging import get_logger

logger = get_logger(__name__)

_HTTPHandler = Callable[..., Awaitable[Response]]

_CHAT_PATHS = frozenset({"/chat", "/chat/stream"})
_request_timestamps: dict[str, list[float]] = defaultdict(list)


class RateLimitMiddleware:
    """Sliding-window rate limiter par IP pour les endpoints /chat."""

    def __init__(self, app: ASGIApp, max_requests: int, window_sec: int) -> None:
        self.app = app
        self.max_requests = max_requests
        self.window_sec = window_sec

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope.get("path") in _CHAT_PATHS:
            key: str = scope.get("client", ("unknown",))[0]
            now = time.time()
            cutoff = now - self.window_sec
            _request_timestamps[key] = [t for t in _request_timestamps[key] if t > cutoff]
            if len(_request_timestamps[key]) >= self.max_requests:
                resp = JSONResponse(
                    status_code=429, content={"detail": "too many requests, try again later"}
                )
                await resp(scope, receive, send)
                return
            _request_timestamps[key].append(now)
        await self.app(scope, receive, send)


def setup_middlewares(app: FastAPI, max_requests: int, window_sec: int) -> None:
    """Attache tous les middlewares a l'application."""
    app.add_middleware(RateLimitMiddleware, max_requests=max_requests, window_sec=window_sec)

    @app.middleware("http")
    async def correlation_id_middleware(request: Request, call_next: _HTTPHandler) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
