"""Synthesis evaluator: composite quality metric for deliberation outputs.

Equivalent to autoresearch's val_bpb — a single number that captures
how productive a deliberation was.
"""

import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Citation pattern: [PUBMED:xxx], [INTERNAL:xxx], [WEB:xxx]
_CITATION_RE = re.compile(r"\[(PUBMED|INTERNAL|WEB):[^\]]+\]")

# Action-oriented phrases that suggest next steps
_ACTION_PHRASES = [
    "next step",
    "should investigate",
    "recommend",
    "further study",
    "propose",
    "suggests that",
    "warrants",
    "should be tested",
    "follow-up",
    "action item",
]


class SynthesisEvaluator:
    """Evaluates deliberation synthesis quality with a composite metric.

    Components (0-1 each, weighted):
    - consensus_strength: ratio of agreements to total claims
    - evidence_density: citations per conclusion
    - novelty: new conclusions not in prior memories
    - actionability: conclusions that suggest next steps
    """

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
    ):
        self.weights = weights or {
            "consensus": 0.25,
            "evidence": 0.30,
            "novelty": 0.25,
            "actionability": 0.20,
        }

    def evaluate(
        self,
        agreements: List[str],
        disagreements: List[str],
        key_conclusions: List[str],
        synthesis_content: str,
        prior_conclusions: Optional[List[str]] = None,
    ) -> float:
        """Compute composite quality score for a synthesis.

        Returns a float in [0, 1].
        """
        scores = {
            "consensus": self._score_consensus(agreements, disagreements),
            "evidence": self._score_evidence(synthesis_content, key_conclusions),
            "novelty": self._score_novelty(key_conclusions, prior_conclusions or []),
            "actionability": self._score_actionability(key_conclusions),
        }

        total = sum(scores[k] * self.weights.get(k, 0) for k in scores)
        return min(max(total, 0.0), 1.0)

    def _score_consensus(self, agreements: List[str], disagreements: List[str]) -> float:
        """Ratio of agreements to total claims."""
        total = len(agreements) + len(disagreements)
        if total == 0:
            return 0.5  # No claims = neutral
        return len(agreements) / total

    def _score_evidence(self, synthesis_content: str, key_conclusions: List[str]) -> float:
        """Citation density: citations found per conclusion."""
        num_conclusions = max(len(key_conclusions), 1)
        citations = _CITATION_RE.findall(synthesis_content)
        # Target: ~2 citations per conclusion = score of 1.0
        return min(len(citations) / (num_conclusions * 2), 1.0)

    def _score_novelty(self, key_conclusions: List[str], prior_conclusions: List[str]) -> float:
        """Fraction of conclusions that are new (not in prior memories).

        Uses simple keyword overlap as a heuristic. For production, this
        would use embedding similarity.
        """
        if not key_conclusions:
            return 0.0
        if not prior_conclusions:
            return 1.0  # Everything is novel if no priors

        prior_words = set()
        for c in prior_conclusions:
            prior_words.update(c.lower().split())

        novel_count = 0
        for conclusion in key_conclusions:
            conclusion_words = set(conclusion.lower().split())
            overlap = len(conclusion_words & prior_words) / max(len(conclusion_words), 1)
            if overlap < 0.5:  # Less than 50% word overlap = novel
                novel_count += 1

        return novel_count / len(key_conclusions)

    def _score_actionability(self, key_conclusions: List[str]) -> float:
        """Fraction of conclusions that suggest concrete next steps."""
        if not key_conclusions:
            return 0.0

        actionable_count = 0
        for conclusion in key_conclusions:
            lower = conclusion.lower()
            if any(phrase in lower for phrase in _ACTION_PHRASES):
                actionable_count += 1

        return actionable_count / len(key_conclusions)
