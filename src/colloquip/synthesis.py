"""Template-driven synthesis generator.

Replaces the basic ConsensusMap with structured output following the
subreddit's OutputTemplate. Produces audit chains linking claims to posts
and citations.
"""

import logging
from typing import Dict, List, Optional

from colloquip.llm.interface import LLMInterface
from colloquip.models import (
    AuditChain,
    OutputTemplate,
    Post,
    Synthesis,
    StructuredCitation,
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
            all_claims.append(f"- [Post #{i+1}, {post.agent_id}] {claim}")

    all_questions = []
    for post in posts:
        for q in post.questions_raised:
            all_questions.append(f"- [{post.agent_id}] {q}")

    # Build the section instructions
    section_instructions = []
    for section in template.sections:
        req = "(REQUIRED)" if section.required else "(OPTIONAL)"
        section_instructions.append(
            f"### {section.name} {req}\n{section.description}"
        )

    sections_text = "\n\n".join(section_instructions)

    # Metadata fields
    metadata_text = ""
    if template.metadata_fields:
        metadata_text = (
            "\n\n## Metadata\n"
            "Also provide values for these metadata fields:\n"
            + "\n".join(f"- {field}" for field in template.metadata_fields)
        )

    prompt = f"""## Hypothesis Under Deliberation

{hypothesis}

## Deliberation Summary ({len(posts)} posts from {len(stance_summary)} agents)

### Agent Stance Trajectories
{chr(10).join(f'- **{agent}**: {" → ".join(stances)}' for agent, stances in stance_summary.items())}

### Key Claims Made During Deliberation
{chr(10).join(all_claims[:30])}

### Open Questions
{chr(10).join(all_questions[:15])}

## Full Conversation
{chr(10).join(f'**Post #{i+1} [{post.agent_id}] ({post.stance.value}, {post.phase.value}):**{chr(10)}{post.content}{chr(10)}' for i, post in enumerate(posts[-20:]))}

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
    """Parse the synthesis text into sections based on template headings."""
    sections: Dict[str, str] = {}
    section_names = [s.name for s in template.sections]

    # Also try to parse metadata fields
    current_section = None
    current_content: List[str] = []

    for line in text.split("\n"):
        stripped = line.strip().lower().replace(" ", "_").replace("#", "").strip()

        # Check if this line is a section header
        matched = False
        for name in section_names:
            if name in stripped:
                # Save previous section
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
    """Extract metadata values from synthesis text."""
    metadata: Dict[str, str] = {}
    for field in metadata_fields:
        # Look for "field_name: value" pattern
        for line in text.split("\n"):
            clean = line.strip().lower()
            field_normalized = field.lower().replace("_", " ")
            if field_normalized in clean or field in clean:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    metadata[field] = parts[1].strip()
                    break
    return metadata


def _extract_audit_chains(
    sections: Dict[str, str],
    posts: List[Post],
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

            # Find supporting posts (simple keyword overlap)
            claim_words = set(claim.lower().split())
            supporting = []
            dissenting = []
            for post in posts:
                post_words = set(post.content.lower().split())
                overlap = len(claim_words & post_words) / max(len(claim_words), 1)
                if overlap > 0.2:
                    if post.stance.value == "critical":
                        dissenting.append(post.agent_id)
                    else:
                        supporting.append(post.id)

            if supporting or dissenting:
                chains.append(AuditChain(
                    claim=claim[:200],
                    supporting_post_ids=supporting[:5],
                    dissenting_agents=list(set(dissenting)),
                ))

    return chains[:20]  # Cap at 20 chains


class SynthesisGenerator:
    """Generate structured synthesis from deliberation posts using templates."""

    def __init__(self, llm: LLMInterface):
        self.llm = llm

    async def generate(
        self,
        hypothesis: str,
        posts: List[Post],
        template: OutputTemplate,
        thread_id=None,
    ) -> Synthesis:
        """Generate a template-driven synthesis.

        1. Build synthesis prompt with all posts + template instructions
        2. LLM generates structured sections
        3. Parse into Synthesis model
        4. Extract audit chains (claim → post → citation)
        """
        from uuid import uuid4

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
                "Synthesis generation failed. Please review the deliberation posts. "
                f"Error: {e}"
            )

        # Parse sections
        sections = _parse_synthesis_sections(raw_text, template)

        # If parsing didn't find sections, put everything in a fallback section
        if not sections:
            sections = {"raw_synthesis": raw_text}

        # Parse metadata
        metadata = _parse_metadata(raw_text, template.metadata_fields)

        # Extract audit chains
        audit_chains = _extract_audit_chains(sections, posts)

        return Synthesis(
            id=uuid4(),
            thread_id=thread_id or uuid4(),
            template_type=template.template_type,
            sections=sections,
            metadata=metadata,
            audit_chains=audit_chains,
        )
