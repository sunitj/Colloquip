"""Cost tracking for deliberation threads.

Tracks token usage and estimated costs per thread, with budget enforcement.
"""

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)

# Default pricing (Claude Sonnet 4.5)
_DEFAULT_INPUT_COST = 0.000003  # $3 per 1M input tokens
_DEFAULT_OUTPUT_COST = 0.000015  # $15 per 1M output tokens


class CostTracker:
    """Track token usage and estimated costs per deliberation thread.

    Records each LLM call's token usage and computes running totals.
    Supports budget enforcement — returns True/False on budget check.
    """

    def __init__(
        self,
        cost_per_input_token: float = _DEFAULT_INPUT_COST,
        cost_per_output_token: float = _DEFAULT_OUTPUT_COST,
    ):
        self.cost_per_input_token = cost_per_input_token
        self.cost_per_output_token = cost_per_output_token

        # thread_id -> list of (input_tokens, output_tokens, model)
        self._records: Dict[UUID, List[dict]] = defaultdict(list)
        self._start_times: Dict[UUID, datetime] = {}

    def start_tracking(self, thread_id: UUID):
        """Mark the start of a thread for duration tracking."""
        self._start_times[thread_id] = datetime.now(timezone.utc)

    def record(
        self,
        thread_id: UUID,
        input_tokens: int,
        output_tokens: int,
        model: str = "default",
    ):
        """Record a single LLM call's token usage."""
        cost = (
            input_tokens * self.cost_per_input_token
            + output_tokens * self.cost_per_output_token
        )
        self._records[thread_id].append({
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "model": model,
            "estimated_cost_usd": cost,
            "recorded_at": datetime.now(timezone.utc),
        })

    def total_tokens(self, thread_id: UUID) -> int:
        """Total tokens (input + output) for a thread."""
        return sum(
            r["input_tokens"] + r["output_tokens"]
            for r in self._records.get(thread_id, [])
        )

    def total_input_tokens(self, thread_id: UUID) -> int:
        return sum(r["input_tokens"] for r in self._records.get(thread_id, []))

    def total_output_tokens(self, thread_id: UUID) -> int:
        return sum(r["output_tokens"] for r in self._records.get(thread_id, []))

    def estimated_cost(self, thread_id: UUID) -> float:
        """Total estimated cost in USD for a thread."""
        return sum(
            r["estimated_cost_usd"] for r in self._records.get(thread_id, [])
        )

    def num_calls(self, thread_id: UUID) -> int:
        return len(self._records.get(thread_id, []))

    def check_budget(self, thread_id: UUID, max_usd: float) -> bool:
        """Check if thread is within budget. Returns True if OK, False if exceeded."""
        return self.estimated_cost(thread_id) <= max_usd

    def thread_summary(self, thread_id: UUID) -> dict:
        """Get a cost summary for a thread."""
        start = self._start_times.get(thread_id)
        duration = 0.0
        if start:
            duration = (datetime.now(timezone.utc) - start).total_seconds()

        return {
            "thread_id": str(thread_id),
            "total_input_tokens": self.total_input_tokens(thread_id),
            "total_output_tokens": self.total_output_tokens(thread_id),
            "total_tokens": self.total_tokens(thread_id),
            "estimated_cost_usd": round(self.estimated_cost(thread_id), 6),
            "num_llm_calls": self.num_calls(thread_id),
            "duration_seconds": round(duration, 1),
        }

    def all_records(self, thread_id: UUID) -> List[dict]:
        """Get all cost records for a thread."""
        return list(self._records.get(thread_id, []))
