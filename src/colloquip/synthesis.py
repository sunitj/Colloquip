"""Template-driven synthesis generator.

Replaces the basic ConsensusMap with structured output following the
subreddit's OutputTemplate. Produces audit chains linking claims to posts
and citations.
"""

import logging
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from colloquip.llm.interface import LLMInterface
from colloquip.models import (
    AgentStance,
    AuditChain,
    OutputTemplate,
    Post,
    Synthesis,
)

logger = logging.getLogger(__name__)


def _build_synthesis_prompt(
    hypothesis: str,
    posts: List[Post],
    template: OutputTemplate,
) -> str:
    """Build the synthesis prompt with template instructions."""
    # Agent stance trajectories
    stance_summary: Dict[str, List[str]] = {}
    for post in posts:
        stance_summary.setdefault(post.agent_id, []).append(post.stance.value)

    # Collect all claims and questions
    all_claims = []
    for i, post in enumerate(posts):
        for claim in post.key_claims:
            all_claims.append(f"- [Post #{i + 1}, {post.agent_id}] {claim}")

    all_questions = []
    for post in posts:
        for q in post.questions_raised:
            all_questions.append(f"- [{post.agent_id}] {q}")

    # Build the section instructions
    section_instructions = []
    for section in template.sections:
        req = "(REQUIRED)" if section.required else "(OPTIONAL)"
        section_instructions.append(f"### {section.name} {req}\n{section.description}")

    sections_text = "\n\n".join(section_instructions)

    # Metadata fields
    metadata_text = ""
    if template.metadata_fields:
        metadata_text = (
            "\n\n## Metadata\n"
            "Also provide values for these metadata fields:\n"
            + "\n".join(f"- {field}" for field in template.metadata_fields)
        )

    trajectories = "\n".join(
        f"- **{agent}**: {' → '.join(stances)}" for agent, stances in stance_summary.items()
    )
    claims_block = "\n".join(all_claims[:30])
    questions_block = "\n".join(all_questions[:15])
    conversation_block = "\n".join(
        f"**Post #{i + 1} [{post.agent_id}] ({post.stance.value}, {post.phase.value}):**\n"
        f"{post.content}\n"
        for i, post in enumerate(posts[-20:])
    )

    prompt = f"""## Hypothesis Under Deliberation

{hypothesis}

## Deliberation Summary ({len(posts)} posts from {len(stance_summary)} agents)

### Agent Stance Trajectories
{trajectories}

### Key Claims Made During Deliberation
{claims_block}

### Open Questions
{questions_block}

## Full Conversation
{conversation_block}

## Task: Generate Structured Synthesis

You must produce a synthesis following this EXACT template structure.
Output each section as a markdown heading followed by content.
Every factual claim MUST cite a source: [PUBMED:PMID], [INTERNAL:ID], or [WEB:URL].
Distinguish between: DIRECT EVIDENCE, INFERENCE, and EXPERT OPINION.

{sections_text}
{metadata_text}

## Important Guidelines

- Do NOT fabricate citations. If evidence was not cited in the deliberation, say so.
- Preserve minority positions — they may prove correct.
- Be specific: use numbers, gene names, compound names, not vague language.
- If agents disagreed, represent BOTH sides fairly.
- The Red Team's concerns should be explicitly addressed, not dismissed.
- Format metadata values on their own line as: `metadata_key: value`
"""

    return prompt


def _parse_synthesis_sections(
    text: str,
    template: OutputTemplate,
) -> Dict[str, str]:
    """Parse the synthesis text into sections based on template headings.

    Matches markdown headings (### Section Name) to template section names.
    Uses exact match after normalization to avoid partial matches
    (e.g., 'summary' matching inside 'executive_summary').
    """
    sections: Dict[str, str] = {}
    # Sort section names longest-first so more specific names match first
    section_names = sorted(
        [s.name for s in template.sections],
        key=len,
        reverse=True,
    )

    current_section = None
    current_content: List[str] = []

    for line in text.split("\n"):
        # Only consider lines that look like headings
        if not line.strip().startswith("#"):
            if current_section:
                current_content.append(line)
            continue

        # Normalize heading: "### Executive Summary (REQUIRED)" -> "executive_summary"
        normalized = (
            line.strip()
            .lower()
            .replace("#", "")
            .strip()
            .replace(" ", "_")
            # Strip trailing markers like "(required)" or "(optional)"
            .split("(")[0]
            .strip()
            .rstrip("_")
        )

        # Check for section match (exact or starts-with for decorated headings)
        matched = False
        for name in section_names:
            if normalized == name or normalized.startswith(name + "_"):
                if current_section:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = name
                current_content = []
                matched = True
                break

        if not matched and current_section:
            current_content.append(line)

    # Save last section
    if current_section:
        sections[current_section] = "\n".join(current_content).strip()

    return sections


def _parse_metadata(text: str, metadata_fields: List[str]) -> Dict[str, str]:
    """Extract metadata values from synthesis text.

    Looks for lines formatted as 'field_name: value'. Only considers
    lines that start with a metadata field name (possibly with leading
    whitespace/bullets) to avoid matching field names that appear
    incidentally inside section prose.
    """
    metadata: Dict[str, str] = {}
    for field in metadata_fields:
        field_lower = field.lower()
        field_normalized = field_lower.replace("_", " ")
        for line in text.split("\n"):
            stripped = line.strip().lstrip("- ").strip()
            clean = stripped.lower()
            # Line must start with the field name (not just contain it)
            if clean.startswith(field_normalized) or clean.startswith(field_lower):
                parts = stripped.split(":", 1)
                if len(parts) == 2 and parts[1].strip():
                    metadata[field] = parts[1].strip()
                    break
    return metadata


_STOP_WORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "has",
        "have",
        "had",
        "do",
        "does",
        "did",
        "not",
        "no",
        "this",
        "that",
        "it",
        "its",
        "as",
        "if",
        "can",
        "may",
        "will",
        "should",
        "would",
        "could",
        "also",
        "than",
        "more",
        "most",
        "very",
        "all",
        "any",
        "both",
        "each",
        "other",
        "such",
        "into",
        "over",
        "only",
        "some",
        "these",
        "those",
        "which",
        "who",
        "whom",
        "what",
        "when",
        "where",
        "how",
        "about",
        "between",
        "through",
        "during",
        "before",
        "after",
    }
)


def _extract_audit_chains(
    sections: Dict[str, str],
    posts: List[Post],
    max_chains: int = 20,
    overlap_threshold: float = 0.3,
    min_claim_words: int = 3,
) -> List[AuditChain]:
    """Extract audit chains linking synthesis claims to supporting posts."""
    chains = []

    # Look for claims in the evidence_for and evidence_against sections
    for section_name in ("evidence_for", "evidence_against", "key_findings", "top_ideas"):
        content = sections.get(section_name, "")
        if not content:
            continue

        for line in content.split("\n"):
            line = line.strip()
            if not line or not line.startswith("-"):
                continue

            claim = line.lstrip("- ").strip()
            if len(claim) < 10:
                continue

            # Filter stop words for meaningful overlap
            claim_words = set(claim.lower().split()) - _STOP_WORDS
            if len(claim_words) < min_claim_words:
                continue

            supporting = []
            dissenting = []
            for post in posts:
                post_words = set(post.content.lower().split()) - _STOP_WORDS
                common = claim_words & post_words
                overlap = len(common) / max(len(claim_words), 1)
                if overlap > overlap_threshold:
                    if post.stance == AgentStance.CRITICAL:
                        dissenting.append(post.agent_id)
                    else:
                        supporting.append(post.id)

            if supporting or dissenting:
                chains.append(
                    AuditChain(
                        claim=claim[:200],
                        supporting_post_ids=supporting[:5],
                        dissenting_agents=list(set(dissenting)),
                    )
                )

    return chains[:max_chains]


def parse_synthesis(
    raw_text: str,
    template: OutputTemplate,
    posts: Optional[List[Post]] = None,
    thread_id: Optional[UUID] = None,
    max_audit_chains: int = 20,
    overlap_threshold: float = 0.3,
    min_claim_words: int = 3,
) -> Synthesis:
    """Parse raw synthesis text into a Synthesis model.

    Testable without LLM — pass any text and get structured output.
    Used by SynthesisGenerator.generate() and available for direct testing.
    """
    sections = _parse_synthesis_sections(raw_text, template)
    if not sections:
        sections = {"raw_synthesis": raw_text.strip() or "No synthesis content generated."}

    metadata = _parse_metadata(raw_text, template.metadata_fields)
    audit_chains = _extract_audit_chains(
        sections,
        posts or [],
        max_chains=max_audit_chains,
        overlap_threshold=overlap_threshold,
        min_claim_words=min_claim_words,
    )

    return Synthesis(
        id=uuid4(),
        thread_id=thread_id or uuid4(),
        template_type=template.template_type,
        sections=sections,
        metadata=metadata,
        audit_chains=audit_chains,
    )


class SynthesisGenerator:
    """Generate structured synthesis from deliberation posts using templates."""

    def __init__(self, llm: LLMInterface):
        self.llm = llm

    async def generate(
        self,
        hypothesis: str,
        posts: List[Post],
        template: OutputTemplate,
        thread_id: Optional[UUID] = None,
    ) -> Synthesis:
        """Generate a template-driven synthesis.

        1. Build synthesis prompt with all posts + template instructions
        2. LLM generates structured sections
        3. Parse into Synthesis model
        4. Extract audit chains (claim → post → citation)
        """
        prompt = _build_synthesis_prompt(hypothesis, posts, template)

        try:
            raw_text = await self.llm.generate_synthesis(
                system_prompt=(
                    "You are a senior scientific deliberation synthesizer. "
                    "Your role is to produce a rigorous, structured synthesis of a "
                    "multi-agent deliberation. Follow the template exactly. "
                    "Every factual claim must cite a source. "
                    "Preserve minority positions. Be specific, not vague."
                ),
                user_prompt=prompt,
            )
        except Exception as e:
            logger.error("Synthesis generation failed: %s", e)
            raw_text = (
                f"Synthesis generation failed. Please review the deliberation posts. Error: {e}"
            )

        return parse_synthesis(
            raw_text=raw_text,
            template=template,
            posts=posts,
            thread_id=thread_id,
        )
