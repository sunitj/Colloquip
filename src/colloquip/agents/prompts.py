"""Prompt builder for deliberation agents.

Supports versioned prompt sets for systematic tuning.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from colloquip.models import AgentConfig, Phase, Post


# Phase mandates appended to each agent's system prompt
PHASE_MANDATES: Dict[Phase, str] = {
    Phase.EXPLORE: (
        "## Current Phase: EXPLORATION\n\n"
        "You are in exploration mode. Your mandate:\n"
        "- Be SPECULATIVE. Propose ideas even without complete evidence.\n"
        "- Ask 'what if' questions. Explore adjacent domains.\n"
        "- LOWER your evidence threshold. Entertain possibilities.\n"
        "- Don't dismiss ideas prematurely.\n\n"
        "Your goal is to expand the hypothesis space, not constrain it."
    ),
    Phase.DEBATE: (
        "## Current Phase: DEBATE\n\n"
        "You are in debate mode. Your mandate:\n"
        "- DEFEND your positions with specific citations.\n"
        "- CHALLENGE claims that lack evidence.\n"
        "- Demand evidence when others make strong claims.\n"
        "- Be willing to UPDATE your position if shown contradicting data.\n\n"
        "Your goal is to stress-test claims through rigorous challenge."
    ),
    Phase.DEEPEN: (
        "## Current Phase: DEEPENING\n\n"
        "You are in deepening mode. Your mandate:\n"
        "- FOCUS on the most promising thread.\n"
        "- Ignore tangents. Go deep on the core issue.\n"
        "- Propose SPECIFIC next steps that would resolve key uncertainties.\n"
        "- Identify the critical assumptions that must be true.\n\n"
        "Your goal is to drill into the highest-signal question."
    ),
    Phase.CONVERGE: (
        "## Current Phase: CONVERGENCE\n\n"
        "You are in convergence mode. Your mandate:\n"
        "- State your FINAL POSITION clearly and concisely.\n"
        "- Acknowledge remaining uncertainties.\n"
        "- Identify what evidence would change your mind.\n"
        "- Be CONCISE. No new explorations.\n\n"
        "Your goal is to crystallize your assessment for synthesis."
    ),
    Phase.SYNTHESIS: (
        "## Current Phase: SYNTHESIS\n\n"
        "The deliberation is concluding. Provide your final summary."
    ),
}


RESPONSE_GUIDELINES = """
## Response Format

Your response must include:

1. **Content**: Your substantive analysis (2-4 paragraphs)

2. **Stance**: Explicitly state one of:
   - SUPPORTIVE: You believe the hypothesis is strengthened
   - CRITICAL: You believe the hypothesis is weakened
   - NEUTRAL: You see merit in multiple directions
   - NOVEL_CONNECTION: You see an unexpected cross-domain bridge

3. **Key Claims**: List 2-4 discrete claims you are making

4. **Questions Raised**: List 1-3 questions for other agents

5. **Connections Identified**: Note any cross-domain bridges

## Interaction Guidelines

- Build on other agents' contributions
- Challenge respectfully with evidence
- Acknowledge when you update your position
- Note when you disagree with another agent and why
""".strip()


def build_system_prompt(
    config: AgentConfig,
    phase: Phase,
    prompt_version: str = "v1",
) -> str:
    """Build the full system prompt for an agent in a given phase."""
    pv = get_prompt_version(prompt_version)
    mandates = pv.phase_mandates
    guidelines = pv.response_guidelines

    parts = [
        config.persona_prompt.strip(),
        "",
        config.phase_mandates.get(phase, mandates.get(phase, "")),
        "",
        guidelines,
    ]
    return "\n\n".join(parts)


def build_user_prompt(
    hypothesis: str,
    posts: List[Post],
    phase_observation: Optional[str] = None,
    max_history: int = 15,
) -> str:
    """Build the user prompt with conversation history."""
    parts = [f"## Hypothesis Under Deliberation\n\n{hypothesis}"]

    if phase_observation:
        parts.append(f"\n## Observer Note\n\n{phase_observation}")

    if posts:
        parts.append("\n## Conversation History\n")
        recent = posts[-max_history:]
        for post in recent:
            parts.append(
                f"\n**{post.agent_id}** ({post.stance.value}, {post.phase.value}):\n"
                f"{post.content}"
            )

    parts.append(
        "\n\n## Your Turn\n\n"
        "Respond with your analysis. Remember your persona, current phase mandate, "
        "and the response format guidelines."
    )

    return "\n".join(parts)


def build_synthesis_prompt(hypothesis: str, posts: List[Post]) -> str:
    """Build the prompt for final synthesis / ConsensusMap generation."""
    stance_summary: Dict[str, List[str]] = {}
    for post in posts:
        stance_summary.setdefault(post.agent_id, []).append(post.stance.value)

    all_claims = []
    for post in posts:
        for claim in post.key_claims:
            all_claims.append(f"- [{post.agent_id}] {claim}")

    all_questions = []
    for post in posts:
        for q in post.questions_raised:
            all_questions.append(f"- [{post.agent_id}] {q}")

    parts = [
        f"## Hypothesis: {hypothesis}\n",
        f"## Deliberation Summary ({len(posts)} posts)\n",
        "### Agent Stance Trajectories\n",
    ]
    for agent_id, stances in stance_summary.items():
        parts.append(f"- **{agent_id}**: {' → '.join(stances)}")

    parts.append("\n### Key Claims\n")
    parts.extend(all_claims[:20])

    parts.append("\n### Open Questions\n")
    parts.extend(all_questions[:10])

    parts.append(
        "\n\n## Task\n\n"
        "Synthesize this deliberation into a ConsensusMap. Identify:\n"
        "1. Summary: One paragraph overview\n"
        "2. Areas of Agreement\n"
        "3. Areas of Disagreement\n"
        "4. Minority Positions worth preserving\n"
        "5. Serendipitous Connections discovered\n"
        "6. Final stance for each agent"
    )

    return "\n".join(parts)


# ---- Prompt Version Registry ----

@dataclass
class PromptVersion:
    """A versioned set of prompt templates for tuning."""

    version: str
    phase_mandates: Dict[Phase, str]
    response_guidelines: str
    notes: str = ""


# v2: Tighter structure, enforces machine-parseable output, domain-specific cues
_V2_PHASE_MANDATES: Dict[Phase, str] = {
    Phase.EXPLORE: (
        "## Current Phase: EXPLORATION\n\n"
        "You are in exploration mode. Your mandate:\n"
        "- Be SPECULATIVE. Propose ideas even without complete evidence.\n"
        "- Ask 'what if' questions. Explore adjacent domains.\n"
        "- LOWER your evidence threshold. Entertain possibilities.\n"
        "- Don't dismiss ideas prematurely.\n"
        "- ACTIVELY look for cross-domain connections between your field "
        "and other agents' expertise.\n"
        "- Reference specific biological pathways, chemical scaffolds, "
        "or clinical endpoints by name.\n\n"
        "Your goal is to expand the hypothesis space, not constrain it."
    ),
    Phase.DEBATE: (
        "## Current Phase: DEBATE\n\n"
        "You are in debate mode. Your mandate:\n"
        "- DEFEND your positions with specific citations and data.\n"
        "- CHALLENGE claims that lack evidence. Reference the specific "
        "post number (e.g., 'as Agent X claimed in post #3').\n"
        "- Demand evidence when others make strong claims.\n"
        "- Be willing to UPDATE your position if shown contradicting data.\n"
        "- Use domain-specific vocabulary (IC50, Ki, AUC, p-values, "
        "hazard ratios, etc.).\n\n"
        "Your goal is to stress-test claims through rigorous challenge."
    ),
    Phase.DEEPEN: (
        "## Current Phase: DEEPENING\n\n"
        "You are in deepening mode. Your mandate:\n"
        "- FOCUS on the single most promising or contested thread.\n"
        "- Ignore tangents. Go deep on the core mechanistic question.\n"
        "- Propose SPECIFIC experiments or analyses that would resolve "
        "the key uncertainty.\n"
        "- Identify the 2-3 critical assumptions that must hold true.\n\n"
        "Your goal is to drill into the highest-signal question."
    ),
    Phase.CONVERGE: (
        "## Current Phase: CONVERGENCE\n\n"
        "You are in convergence mode. Your mandate:\n"
        "- State your FINAL POSITION in ONE paragraph.\n"
        "- Acknowledge remaining uncertainties explicitly.\n"
        "- Identify what evidence would change your mind.\n"
        "- Be CONCISE. No new explorations. No hedging without substance.\n\n"
        "Your goal is to crystallize your assessment for synthesis."
    ),
    Phase.SYNTHESIS: (
        "## Current Phase: SYNTHESIS\n\n"
        "The deliberation is concluding. Provide your final summary "
        "in structured format."
    ),
}

_V2_RESPONSE_GUIDELINES = """
## Response Format

Structure your response EXACTLY as follows:

### Analysis
Your substantive analysis (2-4 paragraphs). Use domain-specific terminology.
Reference other agents' posts by number when building on or challenging them.

### Stance
State exactly ONE of: SUPPORTIVE, CRITICAL, NEUTRAL, NOVEL_CONNECTION

### Key Claims
- Claim 1 (be specific and falsifiable)
- Claim 2
- Claim 3

### Questions Raised
- Question 1 (directed at a specific agent or domain if possible)
- Question 2

### Connections Identified
- Connection 1 (cross-domain bridge, if any)

## Interaction Guidelines

- Build on other agents' contributions by referencing their post numbers
- Challenge respectfully with specific evidence
- Acknowledge when you update your position and explain why
- Note when you disagree with another agent and provide counter-evidence
- Avoid generic statements; be concrete and domain-specific
""".strip()

PROMPT_VERSIONS: Dict[str, PromptVersion] = {
    "v1": PromptVersion(
        version="v1",
        phase_mandates=PHASE_MANDATES,
        response_guidelines=RESPONSE_GUIDELINES,
        notes="Original baseline prompts. Generic response format.",
    ),
    "v2": PromptVersion(
        version="v2",
        phase_mandates=_V2_PHASE_MANDATES,
        response_guidelines=_V2_RESPONSE_GUIDELINES,
        notes=(
            "Tighter structure: enforces markdown headers for reliable parsing, "
            "domain-specific vocabulary cues, post-number references in debate, "
            "one-paragraph convergence limit."
        ),
    ),
}


def get_prompt_version(version: str = "v1") -> PromptVersion:
    """Retrieve a prompt version by name."""
    if version not in PROMPT_VERSIONS:
        raise ValueError(
            f"Unknown prompt version '{version}'. "
            f"Available: {list(PROMPT_VERSIONS.keys())}"
        )
    return PROMPT_VERSIONS[version]
