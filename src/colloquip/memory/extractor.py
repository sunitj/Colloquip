"""Extract SynthesisMemory from completed deliberation syntheses.

Pure text parsing — no LLM calls. Extracts key conclusions, citations,
agent participation, and confidence/evidence metadata from the synthesis
object and its sections.
"""

import re
from typing import Dict, List, Optional
from uuid import UUID

from colloquip.embeddings.interface import EmbeddingProvider
from colloquip.memory.store import DEFAULT_PRIOR, INITIAL_PRIORS, SynthesisMemory
from colloquip.models import Synthesis

# Citation patterns: [PUBMED:xxx], [INTERNAL:xxx], [WEB:xxx]
_CITATION_PATTERN = re.compile(r"\[(PUBMED|INTERNAL|WEB):([^\]]+)\]")


def extract_citations(text: str) -> List[str]:
    """Extract citation references from text."""
    return [f"{match.group(1)}:{match.group(2)}" for match in _CITATION_PATTERN.finditer(text)]


def extract_key_conclusions(
    sections: Dict[str, str],
    max_conclusions: int = 5,
) -> List[str]:
    """Extract key conclusions from synthesis sections.

    Looks for bullet points in high-signal sections (executive_summary,
    key_findings, recommended_next_steps, evidence_for, top_ideas).
    Falls back to first sentences of any available sections.
    """
    priority_sections = [
        "executive_summary",
        "key_findings",
        "recommended_next_steps",
        "evidence_for",
        "top_ideas",
        "quick_wins",
    ]

    conclusions: List[str] = []
    sections_with_bullets: set = set()

    # First pass: extract bullet points from priority sections
    for section_name in priority_sections:
        content = sections.get(section_name, "")
        if not content:
            continue
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("- ") or line.startswith("* "):
                sections_with_bullets.add(section_name)
                text = line.lstrip("-* ").strip()
                if len(text) > 15 and text not in conclusions:
                    conclusions.append(text)
                    if len(conclusions) >= max_conclusions:
                        return conclusions

    # Second pass: first sentence of sections not already covered by bullets
    if len(conclusions) < max_conclusions:
        for name, content in sections.items():
            if name in ("raw_synthesis",) or name in sections_with_bullets:
                continue
            # Split on sentence-ending period followed by space or end
            sentences = content.split(". ")
            if sentences:
                first = sentences[0].strip().rstrip(".")
                if len(first) > 15 and first not in conclusions:
                    conclusions.append(first)
                    if len(conclusions) >= max_conclusions:
                        break

    return conclusions[:max_conclusions]


def extract_agents_involved(
    audit_chains: list,
    metadata: Dict,
) -> List[str]:
    """Extract the list of agents involved from audit chains and metadata."""
    agents = set()

    # From audit chains (dissenting agents)
    for chain in audit_chains:
        if hasattr(chain, "dissenting_agents"):
            agents.update(chain.dissenting_agents)
        elif isinstance(chain, dict):
            agents.update(chain.get("dissenting_agents", []))

    # From metadata
    if "agents_involved" in metadata:
        val = metadata["agents_involved"]
        if isinstance(val, list):
            agents.update(val)
        elif isinstance(val, str):
            agents.update(a.strip() for a in val.split(","))

    return sorted(agents)


class SynthesisMemoryExtractor:
    """Extract a SynthesisMemory from a completed deliberation.

    Testable without LLM — extraction is pure text parsing.
    Only the embedding step requires the EmbeddingProvider.
    """

    def __init__(self, embedding_provider: EmbeddingProvider):
        self.embedding_provider = embedding_provider

    async def extract(
        self,
        synthesis: Synthesis,
        topic: str,
        subreddit_id: UUID,
        subreddit_name: str,
        agents_involved: Optional[List[str]] = None,
    ) -> SynthesisMemory:
        """Extract a SynthesisMemory from a completed synthesis.

        Args:
            synthesis: The completed Synthesis object
            topic: The thread title / hypothesis
            subreddit_id: The subreddit where this deliberation took place
            subreddit_name: Name of the subreddit
            agents_involved: Optional explicit list of participating agents
        """
        # Build full synthesis text for embedding
        all_text = "\n".join(synthesis.sections.values())

        # Extract key conclusions from sections
        key_conclusions = extract_key_conclusions(synthesis.sections)

        # Extract citations from all section text
        citations_used = extract_citations(all_text)
        # Deduplicate while preserving order
        seen_citations: set = set()
        unique_citations = []
        for c in citations_used:
            if c not in seen_citations:
                seen_citations.add(c)
                unique_citations.append(c)

        # Determine agents involved
        resolved_agents = agents_involved or extract_agents_involved(
            synthesis.audit_chains,
            synthesis.metadata,
        )

        # Extract confidence and evidence quality from metadata
        confidence_level = synthesis.metadata.get("confidence_level", "")
        if not confidence_level:
            confidence_level = synthesis.metadata.get("overall_confidence", "")
        evidence_quality = synthesis.metadata.get("evidence_quality", "")

        # Initialize Bayesian priors from the confidence_level string
        prior = INITIAL_PRIORS.get(confidence_level.lower(), DEFAULT_PRIOR)
        conf_alpha, conf_beta = prior

        # Generate embedding from topic + key conclusions
        embed_text = topic
        if key_conclusions:
            embed_text += " " + " ".join(key_conclusions)
        embedding = await self.embedding_provider.embed(embed_text)

        return SynthesisMemory(
            thread_id=synthesis.thread_id,
            subreddit_id=subreddit_id,
            subreddit_name=subreddit_name,
            topic=topic,
            synthesis_content=all_text,
            key_conclusions=key_conclusions,
            citations_used=unique_citations,
            agents_involved=resolved_agents,
            template_type=synthesis.template_type,
            confidence_level=confidence_level,
            evidence_quality=evidence_quality,
            confidence_alpha=conf_alpha,
            confidence_beta=conf_beta,
            embedding=embedding,
        )
