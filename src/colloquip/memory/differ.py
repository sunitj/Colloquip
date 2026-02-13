"""Deliberation differ: compares two syntheses to identify changes.

Produces a structured diff showing new evidence, changed conclusions,
resolved disagreements, and persistent uncertainties.
"""

import logging
from datetime import datetime, timezone
from typing import List
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from colloquip.memory.store import SynthesisMemory

logger = logging.getLogger(__name__)


class DeliberationDiff(BaseModel):
    """Structured diff between two deliberations on related topics."""

    id: UUID = Field(default_factory=uuid4)
    earlier_memory_id: UUID
    later_memory_id: UUID
    new_evidence: List[str] = Field(default_factory=list)
    changed_conclusions: List[str] = Field(default_factory=list)
    resolved_disagreements: List[str] = Field(default_factory=list)
    persistent_uncertainties: List[str] = Field(default_factory=list)
    overall_trajectory: str = ""  # e.g. "converging", "diverging", "stable"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def format_for_prompt(self) -> str:
        """Format the diff for injection into agent prompts."""
        sections = ["## Changes Since Previous Deliberation"]

        if self.new_evidence:
            sections.append("### New Evidence")
            for e in self.new_evidence:
                sections.append(f"- {e}")

        if self.changed_conclusions:
            sections.append("### Changed Conclusions")
            for c in self.changed_conclusions:
                sections.append(f"- {c}")

        if self.resolved_disagreements:
            sections.append("### Resolved Disagreements")
            for r in self.resolved_disagreements:
                sections.append(f"- {r}")

        if self.persistent_uncertainties:
            sections.append("### Persistent Uncertainties")
            for u in self.persistent_uncertainties:
                sections.append(f"- {u}")

        if self.overall_trajectory:
            sections.append(f"\nOverall trajectory: **{self.overall_trajectory}**")

        return "\n".join(sections)


class MockDeliberationDiffer:
    """Mock differ that compares conclusions using text matching.

    Production implementation would use LLM for semantic comparison.
    """

    def diff(
        self,
        earlier: SynthesisMemory,
        later: SynthesisMemory,
    ) -> DeliberationDiff:
        """Compare two related syntheses and produce a structured diff."""
        earlier_conclusions = set(earlier.key_conclusions)
        later_conclusions = set(later.key_conclusions)

        # New conclusions in later that weren't in earlier
        new_evidence = [c for c in later.key_conclusions if c not in earlier_conclusions]

        # Conclusions in earlier that are no longer in later
        dropped = [c for c in earlier.key_conclusions if c not in later_conclusions]

        # Shared conclusions
        _shared = earlier_conclusions & later_conclusions

        # Build changed conclusions
        changed: List[str] = []
        if dropped:
            for d in dropped:
                changed.append(f"Previously stated: '{d}' — no longer in latest conclusions")

        # Citations comparison
        earlier_cites = set(earlier.citations_used)
        later_cites = set(later.citations_used)
        new_cites = later_cites - earlier_cites

        if new_cites:
            new_evidence.append(f"New citations: {', '.join(sorted(new_cites)[:5])}")

        # Determine trajectory
        if len(new_evidence) > len(dropped):
            trajectory = "expanding"
        elif len(dropped) > len(new_evidence):
            trajectory = "narrowing"
        elif not new_evidence and not dropped:
            trajectory = "stable"
        else:
            trajectory = "evolving"

        return DeliberationDiff(
            earlier_memory_id=earlier.id,
            later_memory_id=later.id,
            new_evidence=new_evidence,
            changed_conclusions=changed,
            overall_trajectory=trajectory,
        )
