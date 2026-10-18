"""FastAPI entry point for the shared Knowledge Brain service."""
from pathlib import Path
from typing import Literal

import logfire
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.storage import (
    create_escalation,
    create_ingestion_job,
    finish_ingestion_job,
    get_escalation,
    get_ingestion_job,
    list_escalations,
    list_approved_knowledge,
    next_knowledge_version,
    resolve_escalation,
)

app = FastAPI(
    title="AI Tech Consultant — Knowledge Brain",
    version="1.0.0",
    description="Shared, citation-grounded knowledge API for the Inbox Agent and Meeting-to-Scope.",
)

try:
    logfire.configure(token=settings.LOGFIRE_TOKEN or None, service_name="ai-tech-consultant")
    logfire.instrument_fastapi(app)
except Exception:
    # API availability must not depend on observability configuration.
    pass




def require_api_key(x_api_key: str | None = Header(default=None)):
    """Optional API-key gate: enabled automatically when KNOWLEDGE_API_KEY is set."""
    configured = settings.KNOWLEDGE_API_KEY
    if configured and x_api_key != configured:
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key")
    return True


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=4000)
    top_k: int = Field(default=6, ge=1, le=20)


class EscalationRequest(BaseModel):
    question: str = Field(min_length=3, max_length=4000)
    reason: str = Field(min_length=3, max_length=2000)
    evidence: list[dict] = Field(default_factory=list, max_length=20)


class ResolveRequest(BaseModel):
    answer: str = Field(min_length=3, max_length=10000)
    sources: list[str] = Field(default_factory=list, max_length=20)


def _run_ingestion(job_id: str):
    try:
        from rag.pipeline import run_pipeline

        result = run_pipeline(
            url="https://support.brilliantdirectories.com/support/sitemap.xml",
            mode="sitemap",
            max_pages=None,
            delay=1.0,
            process_images=True,
            wipe=False,
        )
        finish_ingestion_job(job_id, result=result)
    except Exception as exc:
        finish_ingestion_job(job_id, error=f"{type(exc).__name__}: {exc}")


@app.get("/", tags=["health"])
def home():
    return {
        "service": "knowledge-brain",
        "message": "Knowledge Brain API is running.",
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "service": "knowledge-brain"}


@app.post("/query", tags=["knowledge"], dependencies=[Depends(require_api_key)])
def query_knowledge(request: QueryRequest):
    """Return a grounded answer, citations, or a human escalation."""
    from app.query_service import answer_question

    try:
        result = answer_question(request.question, request.top_k)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logfire.exception("Knowledge query failed")
        # Preserve the question instead of fabricating a reply when a dependency fails.
        try:
            escalation = create_escalation(
                request.question,
                reason=f"Knowledge query failed: {type(exc).__name__}: {exc}",
            )
        except Exception:
            escalation = None
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Knowledge service could not complete the query. No answer was fabricated.",
                "escalation_id": escalation["id"] if escalation else None,
            },
        ) from exc

    if result["status"] == "insufficient_evidence" or result.get("needs_human"):
        escalation = create_escalation(
            request.question,
            reason=result.get("reason", "The answer requires human review or evidence is insufficient."),
            evidence=result.get("evidence", []),
        )
        return {
            "answer": result["answer"],
            "status": "needs_human",
            "sources": result["sources"],
            "needs_human": True,
            "escalation_id": escalation["id"],
            "model": result.get("model"),
            "usage": result.get("usage"),
            "estimated_cost_usd": result.get("estimated_cost_usd"),
        }

    return {
        "answer": result["answer"],
        "status": result["status"],
        "sources": result["sources"],
        "needs_human": result["needs_human"],
        "model": result.get("model"),
        "usage": result.get("usage"),
        "estimated_cost_usd": result.get("estimated_cost_usd"),
    }


@app.post("/escalations", tags=["escalations"], status_code=201, dependencies=[Depends(require_api_key)])
def create_escalation_endpoint(request: EscalationRequest):
    return create_escalation(request.question, request.reason, request.evidence)


@app.get("/escalations", tags=["escalations"], dependencies=[Depends(require_api_key)])
def get_escalations(status: Literal["open", "resolved"] | None = None, limit: int = 100):
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 500")
    return {"items": list_escalations(status=status, limit=limit)}


@app.get("/escalations/{escalation_id}", tags=["escalations"], dependencies=[Depends(require_api_key)])
def get_escalation_endpoint(escalation_id: str):
    item = get_escalation(escalation_id)
    if not item:
        raise HTTPException(status_code=404, detail="Escalation not found")
    return item


@app.post("/escalations/{escalation_id}/resolve", tags=["escalations"], dependencies=[Depends(require_api_key)])
def resolve_escalation_endpoint(escalation_id: str, request: ResolveRequest):
    current = get_escalation(escalation_id)
    if not current:
        raise HTTPException(status_code=404, detail="Escalation not found")
    if current["status"] != "open":
        raise HTTPException(status_code=409, detail="Escalation is already resolved")

    proposed = {
        **current,
        "expert_answer": request.answer,
        "answer_sources": request.sources,
        "knowledge_version": next_knowledge_version(escalation_id),
    }
    try:
        from app.query_service import index_approved_answer
        index_approved_answer(proposed)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Answer was not marked resolved because indexing failed: {type(exc).__name__}: {exc}",
        ) from exc

    resolved = resolve_escalation(escalation_id, request.answer, request.sources)
    if not resolved:
        raise HTTPException(status_code=409, detail="Escalation could not be resolved")
    return resolved


@app.get("/knowledge/approved", tags=["escalations"], dependencies=[Depends(require_api_key)])
def approved_knowledge(limit: int = 100):
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 500")
    return {"items": list_approved_knowledge(limit=limit)}


@app.post("/ingestion/run", tags=["ingestion"], status_code=202, dependencies=[Depends(require_api_key)])
def start_ingestion(background_tasks: BackgroundTasks):
    """Queue a full sitemap sync. The crawler itself enforces per-page delays."""
    job_id = create_ingestion_job()
    background_tasks.add_task(_run_ingestion, job_id)
    return {"job_id": job_id, "status": "running"}


@app.get("/ingestion/status", tags=["ingestion"], dependencies=[Depends(require_api_key)])
def ingestion_status(job_id: str | None = None):
    job = get_ingestion_job(job_id)
    manifest_path = Path(__file__).resolve().parent.parent / "ingestion" / "manifest.json"
    counts = {"processed": 0, "failed": 0, "removed": 0, "processing": 0}
    if manifest_path.exists():
        import json
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for entry in manifest.values():
                status = entry.get("status", "unknown")
                if status in counts:
                    counts[status] += 1
        except (OSError, json.JSONDecodeError):
            raise HTTPException(status_code=500, detail="Ingestion manifest is unreadable")
    return {"latest_job": job, "manifest_counts": counts}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
