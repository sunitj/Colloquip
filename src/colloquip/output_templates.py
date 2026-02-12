"""Default output templates for the four thinking types.

Each template defines the structured sections that the synthesis generator
will produce. Templates are matched to subreddits via their ThinkingType.
"""

from colloquip.models import OutputSection, OutputTemplate, ThinkingType

# ---------------------------------------------------------------------------
# ASSESSMENT — "Should we pursue this target/compound/approach?"
# ---------------------------------------------------------------------------
ASSESSMENT_TEMPLATE = OutputTemplate(
    template_type=ThinkingType.ASSESSMENT.value,
    sections=[
        OutputSection(
            name="executive_summary",
            description=(
                "2-3 paragraph overview of the hypothesis, the panel's overall assessment, "
                "and the recommended path forward. Include confidence level."
            ),
        ),
        OutputSection(
            name="evidence_for",
            description=(
                "Bulleted list of evidence supporting the hypothesis. "
                "Each point must include citation references [PUBMED:PMID] or [INTERNAL:ID]. "
                "Group by evidence type: genetic, preclinical, clinical, mechanistic."
            ),
        ),
        OutputSection(
            name="evidence_against",
            description=(
                "Bulleted list of evidence challenging or contradicting the hypothesis. "
                "Include citation references. Note the strength of each counter-argument."
            ),
        ),
        OutputSection(
            name="key_risks",
            description=(
                "Top 3-5 risks that could derail the hypothesis. "
                "For each risk: description, likelihood (low/medium/high), "
                "impact (low/medium/high), and potential mitigation."
            ),
        ),
        OutputSection(
            name="minority_positions",
            description=(
                "Substantive positions held by one or more agents that the majority "
                "did not adopt. Preserve these — they may prove prescient."
            ),
        ),
        OutputSection(
            name="recommended_next_steps",
            description=(
                "Ranked list of 3-5 concrete next steps. Each must be actionable: "
                "who should do what, with what resources, and what the expected "
                "timeline and success criteria are."
            ),
        ),
        OutputSection(
            name="decision_framework",
            description=(
                "Go/No-Go/Conditional framework. State the conditions under which "
                "the panel recommends proceeding, pausing, or stopping. "
                "Include specific data thresholds where possible."
            ),
        ),
    ],
    metadata_fields=[
        "confidence_level",  # high, medium, low
        "evidence_quality",  # strong, moderate, weak
        "consensus_strength",  # unanimous, majority, divided
        "red_team_severity",  # critical, moderate, minor
        "estimated_timeline",  # if applicable
    ],
)


# ---------------------------------------------------------------------------
# REVIEW — "What does this paper/dataset tell us?"
# ---------------------------------------------------------------------------
REVIEW_TEMPLATE = OutputTemplate(
    template_type=ThinkingType.REVIEW.value,
    sections=[
        OutputSection(
            name="publication_summary",
            description=(
                "Structured summary of the publication or dataset: "
                "key findings, methods, sample size, statistical significance."
            ),
        ),
        OutputSection(
            name="internal_data_comparison",
            description=(
                "How do the findings compare with our internal data? "
                "Agreements, contradictions, and novel observations. "
                "Reference specific internal records [INTERNAL:ID]."
            ),
        ),
        OutputSection(
            name="strengths",
            description=(
                "Methodological and scientific strengths of the publication. "
                "What was done well? What can we learn from their approach?"
            ),
        ),
        OutputSection(
            name="limitations",
            description=(
                "Methodological weaknesses, potential biases, statistical concerns, "
                "missing controls, or scope limitations."
            ),
        ),
        OutputSection(
            name="gaps_identified",
            description=(
                "What questions does this work leave unanswered? "
                "What experiments or analyses are needed to confirm or extend the findings?"
            ),
        ),
        OutputSection(
            name="action_items",
            description=(
                "Specific actions for our team based on this review. "
                "Experiments to run, datasets to query, hypotheses to test."
            ),
        ),
    ],
    metadata_fields=[
        "publication_quality",
        "relevance_to_program",
        "reproducibility_assessment",
        "impact_level",
    ],
)


# ---------------------------------------------------------------------------
# ANALYSIS — "What does this data mean?"
# ---------------------------------------------------------------------------
ANALYSIS_TEMPLATE = OutputTemplate(
    template_type=ThinkingType.ANALYSIS.value,
    sections=[
        OutputSection(
            name="data_summary",
            description=(
                "Overview of the data under analysis: source, scope, quality, "
                "key observations. Include statistical summaries where relevant."
            ),
        ),
        OutputSection(
            name="key_findings",
            description=(
                "Top 3-5 findings from the analysis, ranked by significance. "
                "Each finding must be supported by specific data points and citations."
            ),
        ),
        OutputSection(
            name="immediate_actions",
            description=(
                "Actions that should be taken now based on these findings. "
                "High-confidence recommendations with clear ownership."
            ),
        ),
        OutputSection(
            name="aspirational_actions",
            description=(
                "Longer-term actions that depend on further validation. "
                "Lower confidence but high potential impact."
            ),
        ),
        OutputSection(
            name="resource_requirements",
            description=(
                "What resources (people, time, budget, tools) are needed to act on the findings?"
            ),
            required=False,
        ),
        OutputSection(
            name="external_context",
            description=(
                "How do these findings fit within the broader field? "
                "Competitive landscape, published literature, regulatory context."
            ),
        ),
    ],
    metadata_fields=[
        "data_quality",
        "analysis_confidence",
        "statistical_significance",
        "novelty_level",
    ],
)


# ---------------------------------------------------------------------------
# IDEATION — "What could we do next?"
# ---------------------------------------------------------------------------
IDEATION_TEMPLATE = OutputTemplate(
    template_type=ThinkingType.IDEATION.value,
    sections=[
        OutputSection(
            name="opportunity_landscape",
            description=(
                "Overview of the opportunity space. What problem are we solving? "
                "What's the unmet need? What approaches exist?"
            ),
        ),
        OutputSection(
            name="top_ideas",
            description=(
                "Ranked list of the top 3-5 ideas generated by the panel. "
                "For each: description, rationale, feasibility assessment, "
                "and key assumptions."
            ),
        ),
        OutputSection(
            name="novel_connections",
            description=(
                "Unexpected cross-domain connections identified during ideation. "
                "These serendipitous insights may be the most valuable output."
            ),
        ),
        OutputSection(
            name="quick_wins",
            description=(
                "Ideas that can be tested quickly and cheaply. "
                "Low investment, potentially high signal."
            ),
        ),
        OutputSection(
            name="moonshots",
            description=(
                "High-risk, high-reward ideas that require significant investment "
                "but could be transformative if they work."
            ),
            required=False,
        ),
        OutputSection(
            name="next_steps",
            description=(
                "Concrete next steps to evaluate the top ideas. "
                "Include specific experiments, literature searches, or analyses."
            ),
        ),
    ],
    metadata_fields=[
        "creativity_level",
        "feasibility_assessment",
        "consensus_on_top_pick",
        "resource_level_needed",
    ],
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
DEFAULT_TEMPLATES = {
    ThinkingType.ASSESSMENT: ASSESSMENT_TEMPLATE,
    ThinkingType.REVIEW: REVIEW_TEMPLATE,
    ThinkingType.ANALYSIS: ANALYSIS_TEMPLATE,
    ThinkingType.IDEATION: IDEATION_TEMPLATE,
}


def get_template(thinking_type: ThinkingType) -> OutputTemplate:
    """Get the default output template for a thinking type."""
    if thinking_type not in DEFAULT_TEMPLATES:
        raise ValueError(
            f"No template for thinking type '{thinking_type}'. "
            f"Available: {list(DEFAULT_TEMPLATES.keys())}"
        )
    return DEFAULT_TEMPLATES[thinking_type]
