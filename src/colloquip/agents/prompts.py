"""Prompt builder for deliberation agents."""

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


def build_system_prompt(config: AgentConfig, phase: Phase) -> str:
    """Build the full system prompt for an agent in a given phase."""
    parts = [
        config.persona_prompt.strip(),
        "",
        config.phase_mandates.get(phase, PHASE_MANDATES.get(phase, "")),
        "",
        RESPONSE_GUIDELINES,
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
