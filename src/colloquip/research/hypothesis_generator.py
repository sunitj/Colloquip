"""Hypothesis generator: LLM-based next-hypothesis proposal.

Given a research program, prior memories, and experiment history,
proposes the most promising hypothesis to investigate next.
"""

import logging
from typing import Any, Dict, List

from colloquip.llm.interface import LLMInterface

logger = logging.getLogger(__name__)

_HYPOTHESIS_SYSTEM_PROMPT = """You are a research director guiding an autonomous \
research program. Your job is to propose the single most promising hypothesis \
to investigate next, based on:

1. The research program (human-authored goals and constraints)
2. What has been learned from prior deliberations (institutional memory)
3. The experiment history (which hypotheses worked and which didn't)

Rules:
- Be SPECIFIC and TESTABLE — vague hypotheses waste deliberation time
- Avoid re-investigating discarded directions unless you have a novel angle
- Build on successful results — if something worked, explore adjacent ideas
- If the experiment history shows declining value, propose a fundamentally different direction
- Keep the hypothesis under 200 words
"""


def _format_memories(memories: List[Dict[str, Any]]) -> str:
    """Format synthesis memories for the prompt."""
    if not memories:
        return "No prior deliberation memories available."

    parts = []
    for i, mem in enumerate(memories[:10], 1):
        topic = mem.get("topic", "Unknown topic")
        conclusions = mem.get("key_conclusions", [])
        confidence = mem.get("confidence_alpha", 2.0) / (
            mem.get("confidence_alpha", 2.0) + mem.get("confidence_beta", 1.0)
        )
        conclusion_text = "; ".join(conclusions[:3]) if conclusions else "No conclusions"
        parts.append(f"{i}. **{topic}** (confidence: {confidence:.2f})\n   {conclusion_text}")
    return "\n".join(parts)


def _format_history(history: List[Dict[str, Any]]) -> str:
    """Format experiment history for the prompt."""
    if not history:
        return "No experiments run yet — this is the first iteration."

    parts = []
    for entry in history[-15:]:  # Last 15 iterations
        iteration = entry.get("iteration", "?")
        hypothesis = entry.get("hypothesis", "")
        metric = entry.get("metric", 0.0)
        status = entry.get("status", "unknown")
        parts.append(f"- Iteration {iteration} [{status}] (score: {metric:.3f}): {hypothesis}")
    return "\n".join(parts)


class HypothesisGenerator:
    """Generates next hypotheses for the research loop using an LLM."""

    def __init__(self, llm: LLMInterface):
        self.llm = llm

    async def generate(
        self,
        research_program: str,
        memories: List[Dict[str, Any]],
        experiment_history: List[Dict[str, Any]],
    ) -> str:
        """Generate the next hypothesis to investigate.

        Args:
            research_program: The human-authored research program markdown.
            memories: List of synthesis memory dicts from prior deliberations.
            experiment_history: List of metric_history entries from the research job.

        Returns:
            A hypothesis string suitable for starting a new deliberation.
        """
        user_prompt = self._build_user_prompt(research_program, memories, experiment_history)

        result = await self.llm.generate(
            _HYPOTHESIS_SYSTEM_PROMPT,
            user_prompt,
            max_tokens=500,
        )

        return result.content.strip()

    def _build_user_prompt(
        self,
        research_program: str,
        memories: List[Dict[str, Any]],
        experiment_history: List[Dict[str, Any]],
    ) -> str:
        """Build the user prompt for hypothesis generation."""
        parts = [
            "## Research Program\n",
            research_program or "(No research program defined)",
            "\n## What We've Learned So Far\n",
            _format_memories(memories),
            "\n## Experiment History\n",
            _format_history(experiment_history),
            "\n## Your Task\n",
            "Propose the single most promising hypothesis to investigate next. "
            "Be specific and testable. Explain briefly (1-2 sentences) why this "
            "direction is the best use of the next deliberation.",
        ]
        return "\n".join(parts)
