"""API routes for outcome tracking and agent calibration."""

import logging
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# --- Helpers ---

def _parse_uuid(value: str, label: str = "ID") -> UUID:
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail=f"Invalid {label}: {value!r}")


# --- Schemas ---

class OutcomeReportRequest(BaseModel):
    outcome_type: str = Field(pattern=r"^(confirmed|partially_confirmed|contradicted|inconclusive)$")
    summary: str = Field(min_length=1, max_length=5000)
    evidence: str = ""
    conclusions_evaluated: List[str] = Field(default_factory=list)
    agent_assessments: Dict[str, str] = Field(default_factory=dict)
    reported_by: Optional[str] = None


class OutcomeResponse(BaseModel):
    id: str
    thread_id: str
    subreddit_id: str
    outcome_type: str
    summary: str
    evidence: str
    conclusions_evaluated: List[str]
    agent_assessments: Dict[str, str]
    reported_by: Optional[str]
    created_at: str


class CalibrationReportResponse(BaseModel):
    agent_id: str
    total_evaluations: int
    correct: int
    incorrect: int
    partial: int
    accuracy: float
    domain_accuracy: Dict[str, float]
    systematic_biases: List[str]
    is_meaningful: bool


class CalibrationOverviewResponse(BaseModel):
    total_outcomes: int
    agents_with_data: int
    agents_calibrated: int
    agent_reports: List[CalibrationReportResponse]


# --- Endpoints ---

@router.post("/threads/{thread_id}/outcome")
async def report_outcome(
    request: Request,
    thread_id: str,
    body: OutcomeReportRequest,
) -> OutcomeResponse:
    """Report a real-world outcome for a deliberation thread."""
    from colloquip.feedback.outcome import OutcomeReport

    tracker = getattr(request.app.state, "outcome_tracker", None)
    if tracker is None:
        raise HTTPException(status_code=503, detail="Outcome tracking not initialized")

    tid = _parse_uuid(thread_id, "thread_id")
    # subreddit_id would be looked up from the thread in production
    from uuid import uuid4
    outcome = OutcomeReport(
        thread_id=tid,
        subreddit_id=uuid4(),
        outcome_type=body.outcome_type,
        summary=body.summary,
        evidence=body.evidence,
        conclusions_evaluated=body.conclusions_evaluated,
        agent_assessments=body.agent_assessments,
        reported_by=body.reported_by,
    )
    await tracker.save_outcome(outcome)

    return _format_outcome(outcome)


@router.get("/agents/{agent_id}/calibration")
async def get_agent_calibration(
    request: Request,
    agent_id: str,
) -> CalibrationReportResponse:
    """Get calibration metrics for a specific agent."""
    from colloquip.feedback.calibration import AgentCalibration

    tracker = getattr(request.app.state, "outcome_tracker", None)
    if tracker is None:
        raise HTTPException(status_code=503, detail="Outcome tracking not initialized")

    outcomes = await tracker.list_all(limit=500)
    calibration = AgentCalibration()
    report = calibration.compute_calibration(agent_id, outcomes)

    return CalibrationReportResponse(
        agent_id=report.agent_id,
        total_evaluations=report.total_evaluations,
        correct=report.correct,
        incorrect=report.incorrect,
        partial=report.partial,
        accuracy=report.accuracy,
        domain_accuracy=report.domain_accuracy,
        systematic_biases=report.systematic_biases,
        is_meaningful=report.is_meaningful,
    )


@router.get("/calibration/overview")
async def get_calibration_overview(
    request: Request,
) -> CalibrationOverviewResponse:
    """Get calibration overview across all agents."""
    from colloquip.feedback.calibration import AgentCalibration

    tracker = getattr(request.app.state, "outcome_tracker", None)
    if tracker is None:
        raise HTTPException(status_code=503, detail="Outcome tracking not initialized")

    outcomes = await tracker.list_all(limit=500)
    calibration = AgentCalibration()
    overview = calibration.compute_overview(outcomes)

    return CalibrationOverviewResponse(
        total_outcomes=overview.total_outcomes,
        agents_with_data=overview.agents_with_data,
        agents_calibrated=overview.agents_calibrated,
        agent_reports=[
            CalibrationReportResponse(
                agent_id=r.agent_id,
                total_evaluations=r.total_evaluations,
                correct=r.correct,
                incorrect=r.incorrect,
                partial=r.partial,
                accuracy=r.accuracy,
                domain_accuracy=r.domain_accuracy,
                systematic_biases=r.systematic_biases,
                is_meaningful=r.is_meaningful,
            )
            for r in overview.agent_reports
        ],
    )


# --- Formatters ---

def _format_outcome(o) -> OutcomeResponse:
    return OutcomeResponse(
        id=str(o.id),
        thread_id=str(o.thread_id),
        subreddit_id=str(o.subreddit_id),
        outcome_type=o.outcome_type,
        summary=o.summary,
        evidence=o.evidence,
        conclusions_evaluated=o.conclusions_evaluated,
        agent_assessments=o.agent_assessments,
        reported_by=o.reported_by,
        created_at=str(o.created_at),
    )
