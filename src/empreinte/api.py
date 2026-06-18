"""Point d'entree FastAPI d'Empreinte : sante, upload, extraction, bilan, chat."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from empreinte import __version__
from empreinte.config import get_settings
from empreinte.dependencies import get_audit_log, get_pipeline, get_principal, get_rbac_policy
from empreinte.governance import (
    AccessDeniedError,
    AuditLog,
    Permission,
    Principal,
    RBACPolicy,
    mask_pii,
)
from empreinte.ingestion import IngestionError, document_from_images, render_pdf
from empreinte.logging import configure_logging, get_logger
from empreinte.middleware import setup_middlewares
from empreinte.observability import render_metrics
from empreinte.schemas import ChatAnswer, ExtractionResult, FootprintReport, SourceDocument
from empreinte.services import Pipeline, check_readiness

logger = get_logger(__name__)
configure_logging()


@asynccontextmanager
async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
    yield
    from empreinte.services import _cleanup

    await _cleanup()


app = FastAPI(
    title="Empreinte",
    version=__version__,
    description="Assistant GenAI multimodal on-premise pour le reporting ESG/CSRD.",
    lifespan=lifespan,
)


class HealthResponse(BaseModel):
    """Reponse du endpoint de sante."""

    status: str
    version: str


class DocumentSummary(BaseModel):
    """Resume d'un document uploade."""

    doc_id: str
    title: str
    page_count: int


class DocumentRef(BaseModel):
    """Reference a un document deja uploade."""

    document_id: str = Field(min_length=1)


class ChatRequest(BaseModel):
    """Question reglementaire ESRS/CSRD."""

    question: str = Field(min_length=1, max_length=2000)


def _authorize(
    policy: RBACPolicy, principal: Principal, audit: AuditLog, permission: Permission, resource: str
) -> None:
    try:
        policy.authorize(principal, permission)
    except AccessDeniedError as exc:
        audit.record(principal, action=permission.value, resource=resource, allowed=False)
        raise HTTPException(status_code=403, detail="acces refuse") from exc


async def _require_document(pipeline: Pipeline, doc_id: str) -> SourceDocument:
    document = await pipeline.documents.get(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="document introuvable")
    return document


_cfg = get_settings()
_cors_origins = ["*"] if _cfg.env.lower() == "local" else []
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
setup_middlewares(app, _cfg.rate_limit_max_requests, _cfg.rate_limit_window_sec)


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    """Liveness : verifie que le service repond."""
    return HealthResponse(status="ok", version=__version__)


@app.get("/ready", tags=["system"])
async def ready() -> JSONResponse:
    """Readiness : verifie les backends configures (SQL, Qdrant, vLLM)."""
    checks = await check_readiness()
    ok = all(status == "ok" for status in checks.values())
    return JSONResponse(
        status_code=200 if ok else 503,
        content={"ready": ok, "checks": checks},
    )


@app.get("/metrics", tags=["system"])
async def metrics() -> Response:
    """Exposition Prometheus des compteurs et durees de spans."""
    payload, content_type = render_metrics()
    return Response(content=payload, media_type=content_type)


@app.post("/documents", response_model=DocumentSummary, tags=["documents"])
async def upload_document(
    principal: Annotated[Principal, Depends(get_principal)],
    pipeline: Annotated[Pipeline, Depends(get_pipeline)],
    policy: Annotated[RBACPolicy, Depends(get_rbac_policy)],
    audit: Annotated[AuditLog, Depends(get_audit_log)],
    file: Annotated[UploadFile, File(description="PDF ou image a analyser")],
) -> DocumentSummary:
    """Ingere un document (PDF rendu en pages, ou image) et le persiste."""
    _authorize(policy, principal, audit, Permission.EXTRACT, "documents")
    payload = await file.read()
    doc_id = uuid.uuid4().hex
    title = file.filename or doc_id
    try:
        if (file.filename or "").lower().endswith(".pdf"):
            document = render_pdf(doc_id, title, payload, dpi=get_settings().pdf_render_dpi)
        else:
            document = document_from_images(doc_id, title, [payload])
    except IngestionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await pipeline.documents.save(document)
    audit.record(principal, action="upload", resource=doc_id, allowed=True)
    return DocumentSummary(doc_id=doc_id, title=title, page_count=document.page_count)


@app.post("/extract", response_model=ExtractionResult, tags=["esg"])
async def extract(
    ref: DocumentRef,
    principal: Annotated[Principal, Depends(get_principal)],
    pipeline: Annotated[Pipeline, Depends(get_pipeline)],
    policy: Annotated[RBACPolicy, Depends(get_rbac_policy)],
    audit: Annotated[AuditLog, Depends(get_audit_log)],
) -> ExtractionResult:
    """Extrait les donnees d'activite ESG d'un document deja uploade."""
    _authorize(policy, principal, audit, Permission.EXTRACT, ref.document_id)
    document = await _require_document(pipeline, ref.document_id)
    result = await pipeline.extractor.extract(document)
    audit.record(principal, action="extract", resource=ref.document_id, allowed=True)
    return result


@app.post("/report", response_model=FootprintReport, tags=["esg"])
async def report(
    ref: DocumentRef,
    principal: Annotated[Principal, Depends(get_principal)],
    pipeline: Annotated[Pipeline, Depends(get_pipeline)],
    policy: Annotated[RBACPolicy, Depends(get_rbac_policy)],
    audit: Annotated[AuditLog, Depends(get_audit_log)],
) -> FootprintReport:
    """Calcule le bilan carbone sourcé d'un document deja uploade."""
    _authorize(policy, principal, audit, Permission.REPORT, ref.document_id)
    document = await _require_document(pipeline, ref.document_id)
    extraction = await pipeline.extractor.extract(document)
    footprint = await pipeline.report_builder.build(extraction)
    await pipeline.reports.save(footprint)
    audit.record(principal, action="report", resource=ref.document_id, allowed=True)
    return footprint


@app.post("/chat", response_model=ChatAnswer, tags=["chat"])
async def chat(
    request: ChatRequest,
    principal: Annotated[Principal, Depends(get_principal)],
    pipeline: Annotated[Pipeline, Depends(get_pipeline)],
    policy: Annotated[RBACPolicy, Depends(get_rbac_policy)],
    audit: Annotated[AuditLog, Depends(get_audit_log)],
) -> ChatAnswer:
    """Repond a une question reglementaire ESRS/CSRD, ancree sur le corpus."""
    _authorize(policy, principal, audit, Permission.CHAT, "assistant")
    answer = await pipeline.assistant.answer(request.question)
    audit.record(principal, action="chat", resource="assistant", allowed=True)
    return answer.model_copy(update={"answer": mask_pii(answer.answer)})


@app.post("/chat/stream", tags=["chat"])
async def chat_stream(
    request: ChatRequest,
    principal: Annotated[Principal, Depends(get_principal)],
    pipeline: Annotated[Pipeline, Depends(get_pipeline)],
    policy: Annotated[RBACPolicy, Depends(get_rbac_policy)],
    audit: Annotated[AuditLog, Depends(get_audit_log)],
) -> StreamingResponse:
    """Diffuse la reponse en SSE (un evenement par segment)."""
    _authorize(policy, principal, audit, Permission.CHAT, "assistant")
    audit.record(principal, action="chat_stream", resource="assistant", allowed=True)

    async def _events() -> AsyncIterator[str]:
        async for token in pipeline.assistant.answer_stream(request.question):
            yield f"data: {token}\n\n"

    return StreamingResponse(_events(), media_type="text/event-stream")


@app.exception_handler(Exception)
async def global_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Attrape les exceptions non gerees pour eviter les fuites d'information."""
    if isinstance(exc, HTTPException):
        raise exc
    logger.error("unhandled_exception", error=str(exc), error_type=type(exc).__name__)
    return JSONResponse(status_code=500, content={"detail": "erreur interne"})
