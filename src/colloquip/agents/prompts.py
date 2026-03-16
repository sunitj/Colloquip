"""Prompt builder for deliberation agents.

Supports versioned prompt sets for systematic tuning.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Union

from colloquip.models import AgentConfig, Phase, Post

# Word limits per phase (prompt-level instruction)
PHASE_WORD_LIMITS: Dict[Phase, int] = {
    Phase.EXPLORE: 250,
    Phase.DEBATE: 300,
    Phase.DEEPEN: 250,
    Phase.CONVERGE: 150,
    Phase.SYNTHESIS: 500,
}

# Phase mandates appended to each agent's system prompt
PHASE_MANDATES: Dict[Phase, str] = {
    Phase.EXPLORE: (
        "## Current Phase: EXPLORATION\n\n"
        "You are in exploration mode. Your mandate:\n"
        "- Be SPECULATIVE. Propose ideas even without complete evidence.\n"
        "- Ask 'what if' questions. Explore adjacent domains.\n"
        "- LOWER your evidence threshold. Entertain possibilities.\n"
        "- Don't dismiss ideas prematurely.\n\n"
        "Your goal is to expand the hypothesis space, not constrain it.\n\n"
        f"**WORD LIMIT**: Keep your analysis under {PHASE_WORD_LIMITS[Phase.EXPLORE]} words."
    ),
    Phase.DEBATE: (
        "## Current Phase: DEBATE\n\n"
        "You are in debate mode. Your mandate:\n"
        "- DEFEND your positions with specific citations.\n"
        "- CHALLENGE claims that lack evidence.\n"
        "- Demand evidence when others make strong claims.\n"
        "- Be willing to UPDATE your position if shown contradicting data.\n\n"
        "Your goal is to stress-test claims through rigorous challenge.\n\n"
        f"**WORD LIMIT**: Keep your analysis under {PHASE_WORD_LIMITS[Phase.DEBATE]} words."
    ),
    Phase.DEEPEN: (
        "## Current Phase: DEEPENING\n\n"
        "You are in deepening mode. Your mandate:\n"
        "- FOCUS on the most promising thread.\n"
        "- Ignore tangents. Go deep on the core issue.\n"
        "- Propose SPECIFIC next steps that would resolve key uncertainties.\n"
        "- Identify the critical assumptions that must be true.\n\n"
        "Your goal is to drill into the highest-signal question.\n\n"
        f"**WORD LIMIT**: Keep your analysis under {PHASE_WORD_LIMITS[Phase.DEEPEN]} words."
    ),
    Phase.CONVERGE: (
        "## Current Phase: CONVERGENCE\n\n"
        "You are in convergence mode. Your mandate:\n"
        "- State your FINAL POSITION clearly and concisely.\n"
        "- Acknowledge remaining uncertainties.\n"
        "- Identify what evidence would change your mind.\n"
        "- Be CONCISE. No new explorations.\n\n"
        "Your goal is to crystallize your assessment for synthesis.\n\n"
        f"**WORD LIMIT**: Keep your analysis under {PHASE_WORD_LIMITS[Phase.CONVERGE]} words."
    ),
    Phase.SYNTHESIS: (
        "## Current Phase: SYNTHESIS\n\nThe deliberation is concluding. Provide your final summary."
    ),
}


RESPONSE_GUIDELINES = """
## Response Format

Your response must include:

1. **Content**: Your substantive analysis. Respect the word limit for the current phase.

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
                f"\n**{post.agent_id}** ({post.stance.value}, {post.phase.value}):\n{post.content}"
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
        "Your goal is to expand the hypothesis space, not constrain it.\n\n"
        f"**WORD LIMIT**: Keep your analysis under {PHASE_WORD_LIMITS[Phase.EXPLORE]} words."
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
        "Your goal is to stress-test claims through rigorous challenge.\n\n"
        f"**WORD LIMIT**: Keep your analysis under {PHASE_WORD_LIMITS[Phase.DEBATE]} words."
    ),
    Phase.DEEPEN: (
        "## Current Phase: DEEPENING\n\n"
        "You are in deepening mode. Your mandate:\n"
        "- FOCUS on the single most promising or contested thread.\n"
        "- Ignore tangents. Go deep on the core mechanistic question.\n"
        "- Propose SPECIFIC experiments or analyses that would resolve "
        "the key uncertainty.\n"
        "- Identify the 2-3 critical assumptions that must hold true.\n\n"
        "Your goal is to drill into the highest-signal question.\n\n"
        f"**WORD LIMIT**: Keep your analysis under {PHASE_WORD_LIMITS[Phase.DEEPEN]} words."
    ),
    Phase.CONVERGE: (
        "## Current Phase: CONVERGENCE\n\n"
        "You are in convergence mode. Your mandate:\n"
        "- State your FINAL POSITION in ONE paragraph.\n"
        "- Acknowledge remaining uncertainties explicitly.\n"
        "- Identify what evidence would change your mind.\n"
        "- Be CONCISE. No new explorations. No hedging without substance.\n\n"
        "Your goal is to crystallize your assessment for synthesis.\n\n"
        f"**WORD LIMIT**: Keep your analysis under {PHASE_WORD_LIMITS[Phase.CONVERGE]} words."
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
Your substantive analysis. Respect the word limit for the current phase.
Use domain-specific terminology.
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
            f"Unknown prompt version '{version}'. Available: {list(PROMPT_VERSIONS.keys())}"
        )
    return PROMPT_VERSIONS[version]


# ---------------------------------------------------------------------------
# v3: Subreddit-aware prompts with layered assembly
# ---------------------------------------------------------------------------

_MEMORY_INSTRUCTIONS = """
## Instructions for Using Prior Deliberation Context

You have been provided with summaries of relevant past deliberations. Use them as follows:
- REFERENCE prior conclusions when they are relevant to the current topic
- FLAG any contradictions between prior conclusions and current evidence
- DO NOT simply repeat what was concluded before — build on it
- CHECK whether new evidence has emerged that changes prior conclusions
- If prior deliberations reached a conclusion you disagree with, explain why with evidence
""".strip()

_V3_CITATION_INSTRUCTIONS = """
## Citation Requirements

- EVERY factual claim MUST cite a source
- Format: [PUBMED:PMID] for literature, [INTERNAL:record-id] for internal data,
  [WEB:url] for web sources
- If you cannot find evidence, say so explicitly: "No published evidence found for..."
- Distinguish evidence types:
  - DIRECT EVIDENCE: Published data directly supporting/contradicting the claim
  - INFERENCE: Logical extrapolation from related evidence
  - EXPERT OPINION: Your assessment based on domain knowledge (state this explicitly)
- Never fabricate citations. If unsure of a PMID, say "citation needed" instead.
""".strip()

_V3_TOOL_INSTRUCTIONS = """
## Available Research Tools

You have access to the following research tools. Use them to ground your analysis in evidence:

{tool_descriptions}

When you find relevant evidence through these tools, cite it using the appropriate format.
Prefer primary sources (PubMed) over secondary sources.
""".strip()


def build_v3_system_prompt(
    persona_prompt: str,
    phase: Phase,
    phase_mandate: str = "",
    subreddit_context: str = "",
    role_prompt: str = "",
    tool_descriptions: Union[str, List[str]] = "",
    prior_deliberations: str = "",
    research_program: Optional[str] = None,
) -> str:
    """Build a v3 system prompt with layered assembly.

    Layers:
    1. Base persona (from YAML)
    2. Subreddit context (purpose, core questions)
    3. Role in subreddit (membership role_prompt)
    4. Research program (human-authored steering document)
    5. Prior deliberation memory (Phase 3 RAG)
    6. Phase mandate (phase-specific behavior)
    7. Citation requirements
    8. Tool instructions (if tools available)
    9. Response guidelines
    """
    parts = [persona_prompt.strip()]

    if subreddit_context:
        parts.append(subreddit_context)

    if role_prompt:
        parts.append(f"## Your Role in This Community\n\n{role_prompt}")

    if research_program:
        parts.append(f"## Research Program\n\n{research_program}")

    # Prior deliberation memory (Phase 3 RAG)
    if prior_deliberations:
        parts.append(prior_deliberations)
        parts.append(_MEMORY_INSTRUCTIONS)

    # Phase mandate: prefer agent-specific, fall back to v2 defaults
    mandate = phase_mandate or _V2_PHASE_MANDATES.get(phase, "")
    if mandate:
        parts.append(mandate)

    # Citation requirements (always included in v3)
    parts.append(_V3_CITATION_INSTRUCTIONS)

    # Tool instructions (only if tools available)
    if tool_descriptions:
        if isinstance(tool_descriptions, list):
            tool_descriptions = "\n".join(f"- {d}" for d in tool_descriptions)
        parts.append(_V3_TOOL_INSTRUCTIONS.format(tool_descriptions=tool_descriptions))
        # Include job proposal instructions when tools are available
        parts.append(_JOB_PROPOSAL_INSTRUCTIONS)

    parts.append(_V2_RESPONSE_GUIDELINES)

    return "\n\n".join(parts)


def build_v3_user_prompt(
    hypothesis: str,
    posts: List[Post],
    phase_observation: Optional[str] = None,
    subreddit_core_questions: Optional[List[str]] = None,
    max_history: int = 15,
) -> str:
    """Build a v3 user prompt with subreddit context."""
    parts = [f"## Hypothesis Under Deliberation\n\n{hypothesis}"]

    if subreddit_core_questions:
        parts.append(
            "## Core Questions for This Community\n\n"
            + "\n".join(f"- {q}" for q in subreddit_core_questions)
        )

    if phase_observation:
        parts.append(f"\n## Observer Note\n\n{phase_observation}")

    if posts:
        parts.append("\n## Conversation History\n")
        recent = posts[-max_history:]
        for i, post in enumerate(recent):
            post_num = len(posts) - len(recent) + i + 1
            parts.append(
                f"\n**Post #{post_num} [{post.agent_id}] "
                f"({post.stance.value}, {post.phase.value}):**\n"
                f"{post.content}"
            )

    parts.append(
        "\n\n## Your Turn\n\n"
        "Respond with your analysis. Remember your persona, current phase mandate, "
        "citation requirements, and the response format guidelines.\n\n"
        "Use your available research tools to find evidence before making claims."
    )

    return "\n".join(parts)


def build_memory_context(retrieved_memories: "RetrievedMemories") -> str:
    """Build the prior deliberation context for injection into prompts.

    Uses RetrievedMemories.format_for_prompt() to produce the text.
    Returns empty string if no memories are available.

    This is a thin wrapper that can be extended later to add filtering,
    relevance thresholds, or annotation handling.
    """
    # Import here to avoid circular dependency
    from colloquip.memory.retriever import RetrievedMemories

    if not isinstance(retrieved_memories, RetrievedMemories):
        return ""

    if not retrieved_memories.arena and not retrieved_memories.global_results:
        return ""

    return retrieved_memories.format_for_prompt()


_JOB_PROPOSAL_INSTRUCTIONS = """
## Computational Pipeline Proposals

You can propose computational jobs to be run. When you believe a specific
computational analysis would advance the deliberation, include a structured
proposal in your response:

### Pipeline Proposal
- **Pipeline**: [Name of the pipeline]
- **Processes**: [List the Nextflow processes from the library to chain]
- **Input Data**: [What data should be provided]
- **Rationale**: [Why this analysis is needed for the deliberation]
- **Expected Output**: [What results would be informative]

Proposals will be reviewed before execution. When job results arrive,
they will be posted as new data in the thread for further discussion.

Available process categories:
- structure_prediction (AlphaFold2, ESMFold, RoseTTAFold)
- sequence_alignment (ColabFold MSA, MMseqs2)
- structure_search (FoldSeek)
- protein_design (ProteinMPNN)
- structure_refinement (Rosetta Relax)
- simulation (Molecular Dynamics / OpenMM)
- analysis (Binding Affinity, Docking)
""".strip()


def build_subreddit_context(
    subreddit_name: str,
    subreddit_description: str,
    thinking_type: str,
    core_questions: Optional[List[str]] = None,
    decision_context: str = "",
) -> str:
    """Build the subreddit context section for the system prompt."""
    parts = [
        f"## Community: r/{subreddit_name}",
        f"\n{subreddit_description}",
        f"\n**Thinking Type**: {thinking_type}",
    ]

    if decision_context:
        parts.append(f"**Decision Context**: {decision_context}")

    if core_questions:
        parts.append("\n**Core Questions**:")
        for q in core_questions:
            parts.append(f"- {q}")

    return "\n".join(parts)
