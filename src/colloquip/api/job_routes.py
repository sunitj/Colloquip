"""API routes for jobs, pipelines, action proposals, and data connections."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from colloquip.models import (
    DataConnection,
    PipelineDefinition,
    PipelineStep,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["jobs"])


# ---- Request/Response Models ----


class CreateJobRequest(BaseModel):
    session_id: str
    thread_id: Optional[str] = None
    agent_id: str
    pipeline_name: str
    pipeline_description: str = ""
    steps: list = Field(default_factory=list)
    parameters: dict = Field(default_factory=dict)
    compute_profile: str = "standard"


class ReviewProposalRequest(BaseModel):
    reviewer: str
    action: str  # "approve" or "reject"
    note: str = ""


class CreateDataConnectionRequest(BaseModel):
    name: str
    description: str = ""
    db_type: str = "postgresql"
    connection_string: str
    read_only: bool = True


# ---- Nextflow Process Library ----


@router.get("/nf-processes")
async def list_nf_processes(request: Request, category: Optional[str] = None):
    """List available Nextflow processes in the library."""
    manager = _get_job_manager(request)
    if not manager:
        # Fall back to loading from YAML directly
        processes = _load_process_catalog()
        if category:
            processes = [p for p in processes if p.get("category") == category]
        return {"processes": processes}

    processes = await _list_processes_from_manager(manager, category)
    return {"processes": processes}


@router.get("/nf-processes/{process_id}")
async def get_nf_process(request: Request, process_id: str):
    """Get details of a specific Nextflow process."""
    manager = _get_job_manager(request)
    if manager:
        proc = manager.pipeline_builder.get_process(process_id)
        if proc:
            return proc.model_dump()

    # Fall back to YAML
    processes = _load_process_catalog()
    for p in processes:
        if p.get("process_id") == process_id:
            return p
    raise HTTPException(status_code=404, detail=f"Process '{process_id}' not found")


# ---- Jobs ----


@router.post("/jobs")
async def create_job(request: Request, body: CreateJobRequest):
    """Create and submit a computational job."""
    manager = _get_job_manager(request)
    if not manager:
        raise HTTPException(status_code=503, detail="Job manager not configured")

    pipeline_steps = [PipelineStep(**s) for s in body.steps]
    pipeline = PipelineDefinition(
        name=body.pipeline_name,
        description=body.pipeline_description,
        steps=pipeline_steps,
        parameters=body.parameters,
    )

    job = await manager.submit_job(
        session_id=UUID(body.session_id),
        agent_id=body.agent_id,
        pipeline=pipeline,
        compute_profile=body.compute_profile,
        thread_id=UUID(body.thread_id) if body.thread_id else None,
    )

    return {"job_id": str(job.id), "status": job.status.value, "error": job.error_message}


@router.get("/jobs/{job_id}")
async def get_job(request: Request, job_id: str):
    """Get job status and results."""
    manager = _get_job_manager(request)
    if not manager:
        raise HTTPException(status_code=503, detail="Job manager not configured")

    job = await manager.get_job(UUID(job_id))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "id": str(job.id),
        "session_id": str(job.session_id),
        "thread_id": str(job.thread_id) if job.thread_id else None,
        "agent_id": job.agent_id,
        "pipeline": job.pipeline.model_dump(),
        "compute_backend": job.compute_backend.value,
        "compute_profile": job.compute_profile,
        "status": job.status.value,
        "nextflow_run_id": job.nextflow_run_id,
        "result_summary": job.result_summary,
        "result_artifacts": [a.model_dump() for a in job.result_artifacts],
        "error_message": job.error_message,
        "submitted_at": job.submitted_at.isoformat() if job.submitted_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "created_at": job.created_at.isoformat(),
    }


@router.get("/jobs")
async def list_jobs(request: Request, session_id: Optional[str] = None):
    """List jobs, optionally filtered by session."""
    manager = _get_job_manager(request)
    if not manager:
        raise HTTPException(status_code=503, detail="Job manager not configured")

    if session_id:
        jobs = await manager.list_jobs(UUID(session_id))
    else:
        jobs = list(manager._jobs.values())

    return {
        "jobs": [
            {
                "id": str(j.id),
                "session_id": str(j.session_id),
                "agent_id": j.agent_id,
                "pipeline_name": j.pipeline.name,
                "status": j.status.value,
                "created_at": j.created_at.isoformat(),
            }
            for j in jobs
        ]
    }


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(request: Request, job_id: str):
    """Cancel a running job."""
    manager = _get_job_manager(request)
    if not manager:
        raise HTTPException(status_code=503, detail="Job manager not configured")

    cancelled = await manager.cancel_job(UUID(job_id))
    if not cancelled:
        raise HTTPException(status_code=400, detail="Job cannot be cancelled")
    return {"status": "cancelled"}


# ---- Action Proposals ----


@router.get("/proposals")
async def list_proposals(request: Request, session_id: str):
    """List pending action proposals for a session."""
    manager = _get_job_manager(request)
    if not manager:
        raise HTTPException(status_code=503, detail="Job manager not configured")

    proposals = manager.list_pending_proposals(UUID(session_id))
    return {
        "proposals": [
            {
                "id": str(p.id),
                "session_id": str(p.session_id),
                "agent_id": p.agent_id,
                "action_type": p.action_type,
                "description": p.description,
                "rationale": p.rationale,
                "proposed_pipeline": (
                    p.proposed_pipeline.model_dump() if p.proposed_pipeline else None
                ),
                "status": p.status.value,
                "created_at": p.created_at.isoformat(),
            }
            for p in proposals
        ]
    }


@router.post("/proposals/{proposal_id}/review")
async def review_proposal(request: Request, proposal_id: str, body: ReviewProposalRequest):
    """Approve or reject an action proposal."""
    manager = _get_job_manager(request)
    if not manager:
        raise HTTPException(status_code=503, detail="Job manager not configured")

    if body.action == "approve":
        job = await manager.approve_proposal(
            UUID(proposal_id), reviewer=body.reviewer, note=body.note
        )
        if not job:
            raise HTTPException(status_code=404, detail="Proposal not found or not pending")
        return {
            "status": "approved",
            "job_id": str(job.id),
            "job_status": job.status.value,
        }
    elif body.action == "reject":
        await manager.reject_proposal(UUID(proposal_id), reviewer=body.reviewer, note=body.note)
        return {"status": "rejected"}
    else:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")


# ---- Data Connections ----


@router.post("/subreddits/{subreddit_id}/data-connections")
async def create_data_connection(
    request: Request, subreddit_id: str, body: CreateDataConnectionRequest
):
    """Configure a database connection for a subreddit."""
    conn = DataConnection(
        subreddit_id=UUID(subreddit_id),
        name=body.name,
        description=body.description,
        db_type=body.db_type,
        connection_string=body.connection_string,
        read_only=body.read_only,
    )

    # Store in memory (would go to DB in production)
    if not hasattr(request.app.state, "data_connections"):
        request.app.state.data_connections = {}
    request.app.state.data_connections[str(conn.id)] = conn

    return {
        "id": str(conn.id),
        "name": conn.name,
        "db_type": conn.db_type,
        "read_only": conn.read_only,
    }


@router.get("/subreddits/{subreddit_id}/data-connections")
async def list_data_connections(request: Request, subreddit_id: str):
    """List data connections for a subreddit."""
    connections = getattr(request.app.state, "data_connections", {})
    filtered = [
        {
            "id": str(c.id),
            "name": c.name,
            "description": c.description,
            "db_type": c.db_type,
            "read_only": c.read_only,
            "enabled": c.enabled,
        }
        for c in connections.values()
        if str(c.subreddit_id) == subreddit_id
    ]
    return {"connections": filtered}


@router.delete("/subreddits/{subreddit_id}/data-connections/{conn_id}")
async def delete_data_connection(request: Request, subreddit_id: str, conn_id: str):
    """Delete a data connection."""
    connections = getattr(request.app.state, "data_connections", {})
    if conn_id in connections:
        del connections[conn_id]
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Connection not found")


# ---- Helpers ----


def _get_job_manager(request: Request):
    """Get the job manager from app state, if configured."""
    return getattr(request.app.state, "job_manager", None)


def _load_process_catalog():
    """Load process catalog from YAML file."""
    import os

    import yaml

    config_path = os.environ.get("NF_PROCESS_LIBRARY_PATH", "./config/nf_processes.yaml")
    try:
        with open(config_path) as f:
            data = yaml.safe_load(f)
        return data.get("processes", [])
    except FileNotFoundError:
        return []
    except Exception as e:
        logger.error("Failed to load process catalog: %s", e)
        return []


async def _list_processes_from_manager(manager, category=None):
    """List processes from the job manager's pipeline builder."""
    catalog = manager.pipeline_builder._catalog
    processes = list(catalog.values())
    if category:
        processes = [p for p in processes if p.category == category]
    return [p.model_dump() for p in processes]
