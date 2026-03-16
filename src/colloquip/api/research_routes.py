"""API routes for autonomous research loops."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from colloquip.models import ResearchJobStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["research"])


# ---- Request/Response Models ----


class CreateResearchJobRequest(BaseModel):
    max_iterations: int = Field(default=50, ge=1, le=500)
    max_cost_usd: float = Field(default=25.0, ge=0.1, le=1000.0)
    max_threads_per_hour: int = Field(default=3, ge=1, le=20)
    max_runtime_hours: float = Field(default=24.0, ge=0.1, le=168.0)


class ResearchJobResponse(BaseModel):
    id: str
    subreddit_id: str
    status: str
    current_iteration: int
    max_iterations: int
    baseline_metric: Optional[float] = None
    best_metric: Optional[float] = None
    total_cost_usd: float
    max_cost_usd: float
    threads_completed: int
    threads_discarded: int
    created_at: str


class ResearchJobDetailResponse(ResearchJobResponse):
    metric_history: List[dict]
    research_program_version: int


# ---- Helpers ----


def _get_research_store(request: Request) -> dict:
    """Get the in-memory research job store from app state."""
    if not hasattr(request.app.state, "research_jobs"):
        request.app.state.research_jobs = {}
    return request.app.state.research_jobs


def _get_platform(request: Request):
    """Get the PlatformManager from app state."""
    pm = getattr(request.app.state, "platform_manager", None)
    if pm is None or not pm._initialized:
        raise HTTPException(status_code=503, detail="Platform not initialized")
    return pm


def _job_to_response(job) -> ResearchJobResponse:
    return ResearchJobResponse(
        id=str(job.id),
        subreddit_id=str(job.subreddit_id),
        status=job.status.value,
        current_iteration=job.current_iteration,
        max_iterations=job.max_iterations,
        baseline_metric=job.baseline_metric,
        best_metric=job.best_metric,
        total_cost_usd=job.total_cost_usd,
        max_cost_usd=job.max_cost_usd,
        threads_completed=len(job.threads_completed),
        threads_discarded=len(job.threads_discarded),
        created_at=job.created_at.isoformat(),
    )


def _job_to_detail(job) -> ResearchJobDetailResponse:
    return ResearchJobDetailResponse(
        id=str(job.id),
        subreddit_id=str(job.subreddit_id),
        status=job.status.value,
        current_iteration=job.current_iteration,
        max_iterations=job.max_iterations,
        baseline_metric=job.baseline_metric,
        best_metric=job.best_metric,
        total_cost_usd=job.total_cost_usd,
        max_cost_usd=job.max_cost_usd,
        threads_completed=len(job.threads_completed),
        threads_discarded=len(job.threads_discarded),
        created_at=job.created_at.isoformat(),
        metric_history=job.metric_history,
        research_program_version=job.research_program_version,
    )


# ---- Endpoints ----


@router.post(
    "/subreddits/{name}/research-jobs",
    response_model=ResearchJobResponse,
)
async def create_research_job(name: str, body: CreateResearchJobRequest, request: Request):
    """Create a new research loop for a subreddit.

    The job is created in 'pending' status. It must be started explicitly.
    """
    from colloquip.models import ResearchJob

    pm = _get_platform(request)
    subreddit = pm.get_subreddit_by_name(name)
    if not subreddit:
        raise HTTPException(status_code=404, detail=f"Subreddit '{name}' not found")

    # Check no active job already exists
    store = _get_research_store(request)
    for existing in store.values():
        if str(existing.subreddit_id) == subreddit["id"] and existing.status in (
            ResearchJobStatus.PENDING,
            ResearchJobStatus.RUNNING,
        ):
            raise HTTPException(
                status_code=409,
                detail="An active research job already exists for this subreddit",
            )

    job = ResearchJob(
        subreddit_id=UUID(subreddit["id"]),
        research_program_version=subreddit.get("research_program_version", 0),
        max_iterations=body.max_iterations,
        max_cost_usd=body.max_cost_usd,
        max_threads_per_hour=body.max_threads_per_hour,
        max_runtime_hours=body.max_runtime_hours,
    )
    store[str(job.id)] = job

    return _job_to_response(job)


@router.get("/subreddits/{name}/research-jobs")
async def list_research_jobs(name: str, request: Request):
    """List research jobs for a subreddit."""
    pm = _get_platform(request)
    subreddit = pm.get_subreddit_by_name(name)
    if not subreddit:
        raise HTTPException(status_code=404, detail=f"Subreddit '{name}' not found")

    store = _get_research_store(request)
    jobs = [_job_to_response(j) for j in store.values() if str(j.subreddit_id) == subreddit["id"]]
    return {"jobs": jobs}


@router.get("/research-jobs/{job_id}", response_model=ResearchJobDetailResponse)
async def get_research_job(job_id: str, request: Request):
    """Get detailed status of a research job including metric history."""
    store = _get_research_store(request)
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Research job not found")
    return _job_to_detail(job)


@router.post("/research-jobs/{job_id}/pause")
async def pause_research_job(job_id: str, request: Request):
    """Pause a running research job."""
    store = _get_research_store(request)
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Research job not found")
    if job.status != ResearchJobStatus.RUNNING:
        raise HTTPException(
            status_code=400, detail=f"Cannot pause job in status '{job.status.value}'"
        )
    job.status = ResearchJobStatus.PAUSED
    return {"status": "paused"}


@router.post("/research-jobs/{job_id}/resume")
async def resume_research_job(job_id: str, request: Request):
    """Resume a paused research job."""
    store = _get_research_store(request)
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Research job not found")
    if job.status != ResearchJobStatus.PAUSED:
        raise HTTPException(
            status_code=400, detail=f"Cannot resume job in status '{job.status.value}'"
        )
    job.status = ResearchJobStatus.RUNNING
    return {"status": "running"}


@router.post("/research-jobs/{job_id}/stop")
async def stop_research_job(job_id: str, request: Request):
    """Stop a research job permanently."""
    store = _get_research_store(request)
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Research job not found")
    stoppable = (ResearchJobStatus.RUNNING, ResearchJobStatus.PAUSED, ResearchJobStatus.PENDING)
    if job.status not in stoppable:
        raise HTTPException(
            status_code=400, detail=f"Cannot stop job in status '{job.status.value}'"
        )
    job.status = ResearchJobStatus.STOPPED
    return {"status": "stopped"}


@router.get("/research-jobs/{job_id}/results")
async def get_research_job_results(job_id: str, request: Request):
    """Get the iteration-by-iteration results log."""
    store = _get_research_store(request)
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Research job not found")
    return {
        "job_id": str(job.id),
        "status": job.status.value,
        "iterations": job.metric_history,
        "best_metric": job.best_metric,
        "total_cost_usd": job.total_cost_usd,
    }
