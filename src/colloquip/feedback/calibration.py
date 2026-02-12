"""Agent calibration: compute accuracy and bias metrics from outcomes.

Calibration is meaningful only after 10+ outcomes have been reported.
Tracks overall accuracy, domain-specific accuracy, and systematic biases.
"""

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from colloquip.feedback.outcome import OutcomeReport

logger = logging.getLogger(__name__)

MIN_OUTCOMES_FOR_CALIBRATION = 10


class CalibrationReport(BaseModel):
    """Calibration metrics for a single agent."""

    agent_id: str
    total_evaluations: int = 0
    correct: int = 0
    incorrect: int = 0
    partial: int = 0
    not_evaluated: int = 0
    accuracy: float = 0.0  # correct / (correct + incorrect + partial)
    domain_accuracy: Dict[str, float] = Field(default_factory=dict)
    systematic_biases: List[str] = Field(default_factory=list)
    is_meaningful: bool = False  # True only with 10+ evaluations
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CalibrationOverview(BaseModel):
    """Overview of calibration across all agents."""

    total_outcomes: int = 0
    agents_with_data: int = 0
    agents_calibrated: int = 0  # With enough data for meaningful stats
    agent_reports: List[CalibrationReport] = Field(default_factory=list)
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentCalibration:
    """Computes calibration metrics from outcome reports.

    Meaningful only after MIN_OUTCOMES_FOR_CALIBRATION outcomes.
    """

    def __init__(
        self,
        min_outcomes: int = MIN_OUTCOMES_FOR_CALIBRATION,
    ):
        self.min_outcomes = min_outcomes

    def compute_calibration(
        self,
        agent_id: str,
        outcomes: List[OutcomeReport],
        subreddit_names: Optional[Dict[UUID, str]] = None,
    ) -> CalibrationReport:
        """Compute calibration metrics for a specific agent.

        Args:
            agent_id: The agent to compute calibration for
            outcomes: All outcome reports that include this agent
            subreddit_names: Optional mapping of subreddit_id -> name for domain breakdown
        """
        subreddit_names = subreddit_names or {}

        # Filter to outcomes that evaluate this agent
        agent_outcomes = [
            o for o in outcomes
            if agent_id in o.agent_assessments
        ]

        correct = 0
        incorrect = 0
        partial = 0
        not_evaluated = 0

        # Track per-domain stats
        domain_correct: Dict[str, int] = defaultdict(int)
        domain_total: Dict[str, int] = defaultdict(int)

        # Track bias signals
        outcome_type_counts: Dict[str, int] = defaultdict(int)

        for outcome in agent_outcomes:
            assessment = outcome.agent_assessments[agent_id]
            domain = subreddit_names.get(outcome.subreddit_id, str(outcome.subreddit_id))

            if assessment == "correct":
                correct += 1
                domain_correct[domain] += 1
            elif assessment == "incorrect":
                incorrect += 1
            elif assessment == "partial":
                partial += 1
            else:
                not_evaluated += 1

            domain_total[domain] += 1
            outcome_type_counts[outcome.outcome_type] += 1

        total = correct + incorrect + partial
        accuracy = correct / total if total > 0 else 0.0

        # Per-domain accuracy
        domain_accuracy = {}
        for domain, count in domain_total.items():
            d_correct = domain_correct.get(domain, 0)
            domain_accuracy[domain] = d_correct / count if count > 0 else 0.0

        # Detect systematic biases
        biases = self._detect_biases(
            agent_id, correct, incorrect, partial,
            outcome_type_counts, domain_accuracy,
        )

        is_meaningful = len(agent_outcomes) >= self.min_outcomes

        return CalibrationReport(
            agent_id=agent_id,
            total_evaluations=len(agent_outcomes),
            correct=correct,
            incorrect=incorrect,
            partial=partial,
            not_evaluated=not_evaluated,
            accuracy=accuracy,
            domain_accuracy=domain_accuracy,
            systematic_biases=biases,
            is_meaningful=is_meaningful,
        )

    def compute_overview(
        self,
        outcomes: List[OutcomeReport],
        subreddit_names: Optional[Dict[UUID, str]] = None,
    ) -> CalibrationOverview:
        """Compute calibration overview across all agents."""
        # Collect all agent IDs
        all_agents = set()
        for outcome in outcomes:
            all_agents.update(outcome.agent_assessments.keys())

        reports = []
        agents_calibrated = 0
        for agent_id in sorted(all_agents):
            report = self.compute_calibration(agent_id, outcomes, subreddit_names)
            reports.append(report)
            if report.is_meaningful:
                agents_calibrated += 1

        return CalibrationOverview(
            total_outcomes=len(outcomes),
            agents_with_data=len(all_agents),
            agents_calibrated=agents_calibrated,
            agent_reports=reports,
        )

    def _detect_biases(
        self,
        agent_id: str,
        correct: int,
        incorrect: int,
        partial: int,
        outcome_type_counts: Dict[str, int],
        domain_accuracy: Dict[str, float],
    ) -> List[str]:
        """Detect systematic biases in agent performance."""
        biases = []
        total = correct + incorrect + partial
        if total < self.min_outcomes:
            return biases

        # Overconfidence bias
        if incorrect > 0 and incorrect / total > 0.4:
            biases.append(
                f"High incorrect rate ({incorrect}/{total}): "
                f"may be overconfident in conclusions"
            )

        # Domain-specific weakness
        overall_accuracy = correct / total if total > 0 else 0.0
        for domain, acc in domain_accuracy.items():
            if acc < 0.3 and acc < overall_accuracy:
                biases.append(f"Weak in domain '{domain}' (accuracy: {acc:.0%})")

        # Contradicted outcome tendency
        contradicted = outcome_type_counts.get("contradicted", 0)
        if contradicted > 0 and contradicted / max(total, 1) > 0.3:
            biases.append(
                f"Conclusions frequently contradicted "
                f"({contradicted}/{total} outcomes)"
            )

        return biases
