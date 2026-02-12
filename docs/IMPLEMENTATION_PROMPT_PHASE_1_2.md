# Emergent Deliberation Platform: Implementation Prompt
# Phase 1-2 — Core Engine + Multi-Subreddit

## Instructions for Coding Agent

You are building an **AI expert panel system** that lets scientists submit hypotheses and receive structured, multi-perspective, fully-cited assessments in minutes instead of scheduling 2-hour cross-functional meetings.

This is Phase 1-2 of a larger platform. Your job is to make the core deliberation experience so good that scientists voluntarily use it weekly. Do not build anything beyond what's specified here — no memory system, no event-driven triggers, no cross-subreddit references. Those come later and depend on real-world usage data from what you build now.

**Read all existing documentation in `docs/` before writing any code.** The thread-level deliberation design is already specified there. Your job is to:
1. Implement that design faithfully
2. Wrap it in the subreddit/agent-pool architecture described here
3. Add cost tracking, audit trails, and human participation
4. Test it end-to-end with real scientific hypotheses

**Technology stack:** Python 3.11+, FastAPI, PostgreSQL, async throughout. Pydantic models for all data structures. SSE for streaming deliberation output. Follow patterns already established in `docs/` (structured agent prompts with phase mandates, energy-based convergence, observer-detected phase transitions).

---

## 1. What You're Building

### The Core Experience

A scientist opens the platform, navigates to `r/target_validation`, and submits:

> "Evaluate GLP-1 receptor agonism as a therapeutic approach for Alzheimer's disease. Consider the epidemiological evidence from diabetes cohorts, the mechanistic basis for neuroprotection, and the feasibility of CNS-penetrant GLP-1R agonist design."

Within 10-15 minutes, they receive a structured assessment:

- **Executive Summary** with a confidence-scored conclusion
- **Evidence For** and **Evidence Against**, every claim citing PubMed sources
- **Key Risks** ranked with mitigation strategies
- **Minority Positions** — what the dissenting agent(s) argued and why
- **Recommended Next Steps** — specific, actionable
- **Decision Framework** — what new evidence would change this assessment

During the deliberation, the scientist can watch it unfold in real-time (SSE streaming), inject questions or redirect focus, and see which agents are contributing what perspectives.

### What This Is NOT

- Not a chatbot — structured expert panels, not conversation
- Not workflow automation — thinks about what should be done, doesn't execute experiments
- Not a search engine — synthesis across sources and perspectives, not information retrieval
- Not a digital twin (yet) — in Phase 1-2, each deliberation is independent. Institutional memory comes in Phase 3+.

### Value Proposition (Day One)

"Submit a hypothesis, get a structured multi-perspective assessment with cited evidence in 15 minutes."

No accumulated data required. No training period. Useful immediately.

---

## 2. Information Architecture

### Structural Metaphor: Reddit

Use Reddit terminology throughout the codebase. It maps cleanly and reduces cognitive overhead.

```
Platform
├── Subreddit (scoped community: its own agents, tools, output format)
│   ├── Thread (single deliberation, human-initiated)
│   │   ├── Post (agent or human contribution)
│   │   └── Synthesis (structured output matching subreddit template)
│   └── Subreddit Config (agent roster, tools, output template, participation model)
├── Agent Pool (all base agents, shared across subreddits)
│   └── Agent (base persona, instantiated per-subreddit via membership)
└── Cost Tracker (token usage and estimated cost per deliberation)
```

### Entity Relationships

```
Subreddit 1──* Thread
Subreddit *──* Agent (via SubredditMembership: scoped role + tool access)
Thread 1──* Post
Agent 1──* Post (via SubredditMembership)
Thread 1──1 Synthesis
Thread 1──1 CostRecord
```

---

## 3. Subreddit System

### 3.1 Subreddit Configuration Schema

```python
class SubredditConfig(BaseModel):
    """Complete configuration for a subreddit."""

    # Identity
    id: UUID
    name: str  # url-safe slug: "target_validation", "literature_review"
    display_name: str
    description: str  # 2-3 sentences: what this subreddit is for

    # Purpose (structured, drives agent recruitment)
    purpose: SubredditPurpose

    # Agent configuration
    agent_roster: List[SubredditMembership]
    min_agents: int = 3
    max_agents: int = 8
    always_include_red_team: bool = True

    # Tool access
    tool_configs: List[ToolConfig]

    # Output format
    output_template: OutputTemplate

    # Human participation model
    participation_model: ParticipationModel

    # Deliberation engine overrides (optional, defaults from docs/ENERGY_MODEL.md)
    engine_overrides: Optional[EngineOverrides] = None

    # Cost controls
    max_cost_per_thread_usd: float = 5.0  # Kill switch if deliberation gets expensive
    monthly_budget_usd: Optional[float] = None

    created_by: UUID
    created_at: datetime
    updated_at: datetime


class SubredditPurpose(BaseModel):
    """
    Structured purpose definition.
    Drives agent recruitment and output template selection.
    """

    thinking_type: ThinkingType
    core_questions: List[str]  # What questions does this subreddit answer
    decision_context: str       # What decision does the output inform
    primary_domain: str         # e.g. "oncology", "infectious_disease"
    secondary_domains: List[str] = []
    required_expertise: List[str]   # Used for agent recruitment
    optional_expertise: List[str] = []


class ThinkingType(str, Enum):
    ASSESSMENT = "assessment"      # Evaluate hypothesis → go/no-go
    ANALYSIS = "analysis"          # Analyze data → action plan
    REVIEW = "review"              # Review literature → comparison with internal knowledge
    IDEATION = "ideation"          # Generate ideas → prioritized opportunities


class ParticipationModel(str, Enum):
    OBSERVER = "observer"          # Humans read output only
    GUIDED = "guided"              # Humans can inject questions mid-deliberation
    PARTICIPANT = "participant"    # Humans post alongside agents
    APPROVER = "approver"          # Deliberation pauses at decision points for human sign-off
```

### 3.2 Output Templates

Each `ThinkingType` has a default output template. The synthesis generator uses this to structure the final output.

```python
class OutputTemplate(BaseModel):
    template_type: str
    sections: List[OutputSection]
    metadata_fields: List[str]


class OutputSection(BaseModel):
    name: str
    description: str  # Instructions for the synthesis generator
    required: bool = True


# ── Default Templates ──

ASSESSMENT_TEMPLATE = OutputTemplate(
    template_type="assessment",
    sections=[
        OutputSection(
            name="Executive Summary",
            description="2-3 sentence conclusion with confidence level (low/medium/high). "
                        "State the bottom line first."
        ),
        OutputSection(
            name="Evidence For",
            description="Key evidence supporting the hypothesis. Every claim must cite "
                        "a specific source [PUBMED:PMID] or [INTERNAL:record-id]. "
                        "Distinguish direct evidence from inference."
        ),
        OutputSection(
            name="Evidence Against",
            description="Key evidence opposing the hypothesis. Same citation requirements. "
                        "Include mechanistic concerns, not just absence of evidence."
        ),
        OutputSection(
            name="Key Risks",
            description="Top 3-5 risks ranked by likelihood × impact. "
                        "Each risk must include a specific mitigation strategy."
        ),
        OutputSection(
            name="Minority Positions",
            description="What the dissenting agent(s) argued. Include their evidence basis. "
                        "This section must not be empty — if consensus was reached, "
                        "explain what the strongest counter-argument was and why it was insufficient."
        ),
        OutputSection(
            name="Recommended Next Steps",
            description="Specific, actionable next steps. Each must be concrete enough "
                        "that a scientist could start executing it. No vague advice."
        ),
        OutputSection(
            name="Decision Framework",
            description="What new evidence would change this assessment? "
                        "Specify: 'If X were shown, the conclusion would shift to Y.'"
        ),
    ],
    metadata_fields=["confidence_level", "evidence_quality", "consensus_strength"]
)

REVIEW_TEMPLATE = OutputTemplate(
    template_type="literature_review",
    sections=[
        OutputSection(
            name="Publication Summary",
            description="Key claims and findings from the paper under review."
        ),
        OutputSection(
            name="Internal Data Comparison",
            description="How findings compare to our internal datasets. "
                        "Cite specific internal records where available."
        ),
        OutputSection(
            name="Agreements",
            description="Where external and internal evidence align. Cite both sources."
        ),
        OutputSection(
            name="Contradictions",
            description="Where external and internal evidence conflict. "
                        "Propose explanations for discrepancies."
        ),
        OutputSection(
            name="Gaps Identified",
            description="What this paper reveals we don't know. "
                        "Distinguish gaps in the field from gaps in our data."
        ),
        OutputSection(
            name="Action Items",
            description="Specific follow-up experiments, analyses, or investigations."
        ),
    ],
    metadata_fields=["relevance_score", "impact_assessment", "urgency"]
)

ANALYSIS_TEMPLATE = OutputTemplate(
    template_type="analysis_plan",
    sections=[
        OutputSection(
            name="Data Summary",
            description="What data triggered this analysis and what it shows."
        ),
        OutputSection(
            name="Key Findings",
            description="Primary findings with statistical context where applicable."
        ),
        OutputSection(
            name="Immediate Actions",
            description="What we can do now with current capabilities and resources."
        ),
        OutputSection(
            name="Aspirational Actions",
            description="What we should try given high potential upside, "
                        "even if it requires new capabilities or investment."
        ),
        OutputSection(
            name="Resource Requirements",
            description="What each proposed action requires (time, equipment, expertise, cost)."
        ),
        OutputSection(
            name="External Context",
            description="What the broader scientific community is doing in this space. "
                        "Cite recent publications."
        ),
    ],
    metadata_fields=["urgency", "confidence_level", "resource_estimate"]
)

IDEATION_TEMPLATE = OutputTemplate(
    template_type="ideation",
    sections=[
        OutputSection(
            name="Opportunity Landscape",
            description="Overview of the opportunity space with key constraints."
        ),
        OutputSection(
            name="Top Ideas",
            description="3-5 ranked ideas. Each must include: rationale, feasibility "
                        "assessment, key assumption, and first validation step."
        ),
        OutputSection(
            name="Novel Connections",
            description="Non-obvious cross-domain insights that emerged during deliberation."
        ),
        OutputSection(
            name="Quick Wins",
            description="Ideas testable with <1 week of effort and existing resources."
        ),
        OutputSection(
            name="Moonshots",
            description="High-risk, high-reward ideas. Include why the upside "
                        "justifies the risk."
        ),
        OutputSection(
            name="Next Steps",
            description="Concrete plan to advance the top 2-3 ideas."
        ),
    ],
    metadata_fields=["novelty_score", "feasibility", "potential_impact"]
)

# Map for lookup
DEFAULT_TEMPLATES = {
    ThinkingType.ASSESSMENT: ASSESSMENT_TEMPLATE,
    ThinkingType.REVIEW: REVIEW_TEMPLATE,
    ThinkingType.ANALYSIS: ANALYSIS_TEMPLATE,
    ThinkingType.IDEATION: IDEATION_TEMPLATE,
}
```

### 3.3 Subreddit Creation Flow

```
Human provides:
  - name, description
  - purpose (structured: thinking_type, core_questions, decision_context, domains, required_expertise)
  - participation_model
  - tool access preferences (which tools agents can use)

System does:
  1. Parse purpose → identify required expertise
  2. Search agent pool for matching agents (by expertise_tags + domain)
  3. For MISSING expertise:
     a. Check curated persona library (backend/agents/personas/*.yaml)
     b. If a curated persona exists for that expertise → propose it
     c. If NO curated persona exists → flag to human: "No {expertise} agent available.
        You can create one from a template or write a custom persona."
     d. DO NOT auto-generate personas via LLM. Curated personas only in Phase 1-2.
  4. Create SubredditMembership for each recruited agent
  5. Ensure at least one Red Team agent (from curated pool)
  6. Select output template based on thinking_type (use defaults above)
  7. Return subreddit config for human review before activation
```

**Critical: No LLM-generated agent personas in Phase 1-2.** The value of multi-agent deliberation comes from productive disagreement between genuinely different perspectives. Hand-crafted personas with specific blind spots, interaction styles, and evaluation priorities produce better deliberations than LLM-generated ones that tend toward generic, safe reasoning. Build a curated library of 8-12 base personas that cover common biotech expertise areas. See Section 4.4.

---

## 4. Agent System

### 4.1 Agent Architecture: Layered Identity

Agents have a **base persona** (who they are) and **subreddit-scoped instances** (what they do in a specific community).

```python
class BaseAgent(BaseModel):
    """
    Core agent identity. Shared across all subreddits the agent participates in.

    This is the "person" — their scientific background, reasoning style,
    evaluation priorities, and known blind spots.

    Follows the prompt architecture in docs/AGENT_PROMPTS.md:
    Core Persona (~2000-4000 tokens) + Phase Mandates (4 phases × ~100 tokens)
    """

    id: UUID
    agent_type: str  # e.g. "biology", "chemistry", "admet", "clinical", "red_team"
    display_name: str
    expertise_tags: List[str]  # Searchable tags for recruitment matching

    # Core persona prompt (loaded from YAML, human-curated)
    persona_prompt: str

    # Phase mandates
    phase_mandates: Dict[str, str]  # Keys: "explore", "debate", "deepen", "converge"

    # Domain keywords for trigger relevance (docs/TRIGGER_RULES.md)
    domain_keywords: List[str]

    # Evaluation criteria with weights (sum to 1.0)
    evaluation_criteria: Dict[str, float]

    is_red_team: bool = False
    status: AgentStatus = AgentStatus.ACTIVE

    created_at: datetime
    version: int = 1  # Increment when persona is updated


class AgentStatus(str, Enum):
    ACTIVE = "active"
    RETIRED = "retired"
    DRAFT = "draft"  # Being authored, not yet available for recruitment


class SubredditMembership(BaseModel):
    """
    An agent's scoped identity within a specific subreddit.

    This is the "role" — what the agent focuses on in this community
    and what tools it can access here.
    """

    id: UUID
    agent_id: UUID
    subreddit_id: UUID

    # Subreddit-specific role (appended to base persona at runtime)
    role_prompt: str
    # e.g. "In r/literature_review, you compare new findings against our internal
    #  assay data. Prioritize identifying contradictions with our existing results."

    # Scoped tool access
    tool_access: List[str]  # Tool IDs this agent can use in this subreddit

    # Participation stats (updated after each thread)
    threads_participated: int = 0
    total_posts: int = 0

    joined_at: datetime
```

### 4.2 Agent Prompt Assembly at Runtime

When an agent generates a post, its prompt is assembled from layers. This is the most performance-critical code path — get it right.

```python
async def build_agent_prompt(
    agent: BaseAgent,
    membership: SubredditMembership,
    subreddit: SubredditConfig,
    phase: str,
    thread_context: ThreadContext,
    available_tools: List[ToolDescription]
) -> str:
    """
    Assemble the full agent prompt for a single deliberation turn.

    Layers (in order):
    1. Base persona — who am I (static, from YAML)
    2. Subreddit role — what do I do here (from membership)
    3. Phase mandate — how should I behave right now (from persona)
    4. Tool instructions — what I can access and citation requirements
    5. Thread context — what's been said so far
    6. Response guidelines — formatting and quality requirements
    """

    prompt = f"""{agent.persona_prompt}

## Your Role in r/{subreddit.name}
{membership.role_prompt}

## Subreddit Context
Purpose: {subreddit.description}
Core questions: {'; '.join(subreddit.purpose.core_questions)}
Decision context: {subreddit.purpose.decision_context}
Output format: {subreddit.output_template.template_type}

## Current Phase: {phase.upper()}
{agent.phase_mandates[phase]}

## Available Tools
{_format_tool_descriptions(available_tools)}

## Citation Requirements
- EVERY factual claim MUST cite a source
- Format: [PUBMED:PMID] for literature, [INTERNAL:record-id] for internal data
- If you cannot find evidence, say so explicitly: "I could not find evidence for..."
- Distinguish: DIRECT EVIDENCE (source explicitly supports claim) vs INFERENCE (claim follows logically from source) vs OPINION (your expert judgment, not sourced)
- Never fabricate citations. Ever.

## Thread So Far
Topic: {thread_context.topic}
{thread_context.initial_post}

{_format_posts(thread_context.posts)}

## Response Guidelines
- Be specific. Cite specific compounds, specific assays, specific papers.
- Disagree when your expertise warrants it. Do not defer to consensus if you have evidence otherwise.
- If another agent made an unsupported claim, call it out.
- Keep your response focused: 150-400 words unless the phase mandates brevity or depth.
- Do not repeat what others have said. Build on it, challenge it, or add new information.
"""
    return prompt


def _format_posts(posts: List[Post]) -> str:
    """Format thread posts for context injection."""
    formatted = []
    for post in posts:
        label = f"[{post.agent_display_name}]" if not post.is_human else "[HUMAN]"
        formatted.append(f"{label} (Phase: {post.phase})\n{post.content}\n")
    return "\n---\n".join(formatted)
```

### 4.3 Agent Recruitment Logic

```python
async def recruit_for_subreddit(
    purpose: SubredditPurpose,
    agent_pool: List[BaseAgent],
    subreddit_id: UUID
) -> RecruitmentResult:
    """
    Match required expertise to existing agents in the pool.

    Returns:
    - memberships: agents successfully recruited
    - gaps: expertise areas with no matching agent

    Algorithm:
    1. For each required_expertise, score all agents by tag overlap + domain match
    2. Assign best match (greedy, no agent assigned twice)
    3. For optional_expertise, assign if good match available
    4. Ensure at least one red_team agent
    5. Report gaps
    """

    assigned_ids = set()
    memberships = []
    gaps = []

    # Required expertise
    for expertise in purpose.required_expertise:
        candidates = _score_candidates(
            expertise=expertise,
            domain=purpose.primary_domain,
            pool=agent_pool,
            exclude=assigned_ids
        )

        if candidates and candidates[0].score > 0.5:
            best = candidates[0].agent
            memberships.append(_create_membership(best, subreddit_id, purpose))
            assigned_ids.add(best.id)
        else:
            gaps.append(ExpertiseGap(
                expertise=expertise,
                domain=purpose.primary_domain,
                has_curated_template=_check_persona_library(expertise)
            ))

    # Optional expertise (best-effort)
    for expertise in purpose.optional_expertise:
        candidates = _score_candidates(expertise, purpose.primary_domain, agent_pool, assigned_ids)
        if candidates and candidates[0].score > 0.7:  # Higher bar for optional
            best = candidates[0].agent
            memberships.append(_create_membership(best, subreddit_id, purpose))
            assigned_ids.add(best.id)

    # Red team (mandatory)
    has_red_team = any(
        _get_agent(m.agent_id, agent_pool).is_red_team
        for m in memberships
    )
    if not has_red_team:
        red_team = next(
            (a for a in agent_pool if a.is_red_team and a.id not in assigned_ids),
            None
        )
        if red_team:
            memberships.append(_create_membership(red_team, subreddit_id, purpose))
        else:
            gaps.append(ExpertiseGap(
                expertise="adversarial_analysis",
                domain=purpose.primary_domain,
                is_red_team=True,
                has_curated_template=True  # We always ship a base red team persona
            ))

    return RecruitmentResult(memberships=memberships, gaps=gaps)


def _score_candidates(
    expertise: str,
    domain: str,
    pool: List[BaseAgent],
    exclude: Set[UUID]
) -> List[ScoredCandidate]:
    """
    Score agents against a required expertise.

    Scoring:
    - exact expertise_tag match: +0.5
    - partial expertise_tag overlap: +0.2 per overlapping token
    - domain keyword match: +0.3
    - already in other subreddits (experienced): +0.1
    """
    ...
```

### 4.4 Curated Persona Library

Ship with a curated set of 8-12 base agent personas. Each is a YAML file in `backend/agents/personas/`. These are hand-written, tested, and tuned — not LLM-generated.

```yaml
# backend/agents/personas/molecular_biology.yaml
agent_type: molecular_biology
display_name: "Molecular Biology Expert"
expertise_tags:
  - molecular_biology
  - cell_biology
  - genetics
  - gene_expression
  - protein_function
  - signal_transduction

persona_prompt: |
  You are a molecular biologist with 15 years of experience in target
  identification and validation. Your background spans academic research
  (postdoc at Broad Institute) and industry (senior scientist at a
  mid-stage biotech). You think mechanistically — you want to understand
  the pathway, not just the correlation.

  ## Evaluation Priorities
  1. Mechanistic evidence (weight: 0.30) — Is the biological mechanism understood?
  2. Genetic validation (weight: 0.25) — Do human genetics support the target?
  3. Reproducibility (weight: 0.20) — Has the finding been independently replicated?
  4. Translational relevance (weight: 0.15) — Does in vitro translate to in vivo?
  5. Novelty of biology (weight: 0.10) — Are we learning something new about the pathway?

  ## Reasoning Style
  You reason from mechanism upward. When presented with a clinical observation,
  your first instinct is to ask "what's the molecular basis?" You're skeptical
  of phenotypic screens without mechanistic follow-up. You trust genetic evidence
  (GWAS, LOF studies, Mendelian disease) more than pharmacological evidence.

  ## Known Blind Spots
  - You overweight mechanistic elegance. A clean pathway story can seduce you
    even when the clinical evidence is weak.
  - You're skeptical of AI/ML-derived targets that lack clear biological rationale,
    even when the predictions have statistical support.
  - You sometimes dismiss clinical observations that don't fit current
    mechanistic models, when the observation should update the model.
  - You underestimate the difficulty of achieving target engagement in vivo.

  ## Interaction Style
  You ask pointed mechanistic questions. When someone claims a target is
  validated, you want to see the LOF data, the tissue expression profile,
  and the pathway analysis. You respect chemistry colleagues but push back
  when they propose targets based purely on druggability without strong
  biological rationale. You're direct but not dismissive.

evaluation_criteria:
  mechanistic_evidence: 0.30
  genetic_validation: 0.25
  reproducibility: 0.20
  translational_relevance: 0.15
  novelty: 0.10

phase_mandates:
  explore: |
    ## EXPLORE Phase Mandate
    Lay out the biological landscape. What is known about this target's
    mechanism? What genetic evidence exists? What model systems have been
    used? Cite specific studies. Identify the 2-3 most important biological
    questions that need answers.
  debate: |
    ## DEBATE Phase Mandate
    Challenge claims that lack mechanistic support. If another agent cited
    a correlation study, ask about causation. If a pathway is proposed,
    ask about alternative pathways. Push on the weakest link in the
    biological argument.
  deepen: |
    ## DEEPEN Phase Mandate
    Go deep on the most contested biological question from the debate phase.
    Bring additional evidence — tissue-specific expression data, genetic
    association results, phenotypic screens in relevant model systems.
    If there's a gap, name it explicitly.
  converge: |
    ## CONVERGE Phase Mandate
    State your biological assessment clearly. Is the target biologically
    validated? What is your confidence level? What single experiment would
    most change your assessment? Be honest about remaining uncertainties.

domain_keywords:
  - gene
  - protein
  - pathway
  - mechanism
  - expression
  - knockout
  - GWAS
  - LOF
  - cell line
  - in vitro
  - signaling
  - transcription
  - phenotype

is_red_team: false
```

**Required personas to ship in Phase 1-2:**

| Persona | File | Key Perspective |
|---|---|---|
| Molecular Biology | `molecular_biology.yaml` | Mechanistic rigor, genetic evidence |
| Medicinal Chemistry | `medicinal_chemistry.yaml` | Druggability, SAR, synthetic feasibility |
| ADMET / Pharmacology | `admet.yaml` | Drug-like properties, PK/PD, safety |
| Clinical Development | `clinical.yaml` | Clinical translatability, trial design, patient selection |
| Regulatory Affairs | `regulatory.yaml` | Regulatory pathway, precedent, risk classification |
| Computational Biology | `computational_biology.yaml` | Data analysis, modeling, statistical rigor |
| Red Team (General) | `red_team_general.yaml` | Adversarial: what could go wrong, hidden assumptions |
| Red Team (Biology) | `red_team_biology.yaml` | Domain-specific failure modes, common biological pitfalls |

Write all 8 persona YAML files with the same depth and specificity as the molecular biology example above. Each must have: specific blind spots, weighted evaluation criteria, distinct reasoning style, and phase mandates that produce genuinely different behavior.

**Quality test for personas:** If you swap two agents' posts in a deliberation and a reader can't tell the difference, the personas are too similar. Each agent must have a recognizable voice and perspective.

---

## 5. Tool System

### 5.1 Tool Registry

```python
class ToolConfig(BaseModel):
    """A tool available within a subreddit."""

    tool_id: str          # "pubmed", "web_search", "internal_assay_db"
    display_name: str
    description: str      # Included in agent prompt to explain capabilities
    tool_type: ToolType
    connection_config: Dict  # API keys, endpoints (stored securely, not in prompt)
    enabled: bool = True


class ToolType(str, Enum):
    LITERATURE_SEARCH = "literature_search"
    INTERNAL_DATABASE = "internal_database"
    WEB_SEARCH = "web_search"
    COMPUTATION = "computation"
```

### 5.2 Tool Implementations (Phase 1-2)

Implement two tools for Phase 1-2. Keep the tool interface simple — agents call tools via structured tool_use in their LLM calls.

```python
class PubMedTool:
    """
    Search PubMed for biomedical literature.

    Wraps PubMed E-utilities API:
    - search: keyword search, returns PMIDs + metadata
    - get_abstract: fetch abstract by PMID
    - get_full_text: fetch full text from PMC if available
    - find_related: find related articles

    Every result must return a structured Citation object
    that agents use in [PUBMED:PMID] references.
    """

    async def search(
        self, query: str, max_results: int = 10, date_from: Optional[str] = None
    ) -> List[Citation]:
        ...

    async def get_abstract(self, pmid: str) -> ArticleAbstract:
        ...

    async def get_full_text(self, pmid: str) -> Optional[str]:
        """Returns full text if available in PMC, None otherwise."""
        ...

    async def find_related(self, pmids: List[str], max_results: int = 5) -> List[Citation]:
        ...


class WebSearchTool:
    """
    General web search for broader context.
    Used for market data, competitive intelligence, recent news.

    Keep results concise — agents should cite specific findings,
    not dump entire web pages into their posts.
    """

    async def search(self, query: str, max_results: int = 5) -> List[WebResult]:
        ...


class Citation(BaseModel):
    """Structured citation that agents use to reference sources."""
    source_type: str         # "pubmed", "internal", "web"
    source_id: str           # PMID, internal record ID, URL
    title: str
    authors: Optional[str]
    year: Optional[int]
    journal: Optional[str]
    snippet: str             # Key finding from this source
    url: Optional[str]
    retrieved_at: datetime
```

### 5.3 Tool Usage in Agent Prompts

Tools are presented as callable functions in the LLM's tool_use interface. The agent decides when and how to use them based on deliberation context.

```python
def format_tool_descriptions(tools: List[ToolConfig]) -> str:
    """Format tools for inclusion in agent prompt."""
    descriptions = []
    for tool in tools:
        descriptions.append(f"- **{tool.display_name}** ({tool.tool_id}): {tool.description}")
    return "\n".join(descriptions)
```

**Critical: Citation audit.** After synthesis generation, run an automated check that every [PUBMED:PMID] reference in the output corresponds to a real paper. Flag hallucinated citations. This is non-negotiable for scientific credibility.

---

## 6. Thread and Deliberation Engine

### 6.1 Thread Lifecycle

```python
class Thread(BaseModel):
    """A single deliberation within a subreddit."""

    id: UUID
    subreddit_id: UUID
    title: str
    initial_post: str          # The hypothesis or question
    status: ThreadStatus
    created_by: UUID           # Human who created it

    # Deliberation state
    current_phase: str         # explore, debate, deepen, converge
    total_posts: int = 0
    total_tokens_used: int = 0
    estimated_cost_usd: float = 0.0

    # Output
    synthesis: Optional[Synthesis] = None

    created_at: datetime
    completed_at: Optional[datetime] = None


class ThreadStatus(str, Enum):
    ACTIVE = "active"           # Deliberation in progress
    PAUSED = "paused"           # Waiting for human input (approver model)
    COMPLETED = "completed"     # Synthesis generated
    FAILED = "failed"           # Engine error or budget exceeded
    CANCELLED = "cancelled"     # Human cancelled


class Post(BaseModel):
    """A single contribution to a thread."""

    id: UUID
    thread_id: UUID
    agent_id: Optional[UUID]   # None for human posts
    is_human: bool = False
    human_id: Optional[UUID]

    phase: str                 # Phase when post was created
    content: str
    citations: List[Citation]  # Extracted from content
    tool_calls: List[ToolCall] # Tools used to generate this post
    tokens_used: int

    # Quality signals (from observer)
    novelty_score: Optional[float] = None
    relevance_score: Optional[float] = None

    created_at: datetime


class Synthesis(BaseModel):
    """Structured output from a completed deliberation."""

    id: UUID
    thread_id: UUID
    template_type: str

    # Structured sections matching the output template
    sections: Dict[str, str]   # section_name → content

    # Metadata
    metadata: Dict[str, Any]   # confidence_level, evidence_quality, etc.

    # Audit trail
    audit_chains: List[AuditChain]  # Claim → supporting posts → citations

    # Quality
    total_citations: int
    citation_verification: CitationVerification  # Results of automated check

    tokens_used: int
    created_at: datetime


class AuditChain(BaseModel):
    """Traceability chain for a claim in the synthesis."""

    claim: str
    supporting_post_ids: List[UUID]  # Posts that contributed this claim
    citations: List[Citation]         # Primary sources
    evidence_type: str                # direct, inference, consensus, opinion
    dissenting_agents: List[str]      # Agents who disagreed, if any


class CitationVerification(BaseModel):
    """Results of automated citation checking."""
    total_citations: int
    verified: int           # Citation exists and is real
    unverified: int         # Could not verify (doesn't mean fake)
    flagged: int            # Likely hallucinated — does not exist
    details: List[Dict]     # Per-citation verification results
```

### 6.2 Deliberation Engine Integration

The engine orchestrates the deliberation loop following the specs in `docs/`:

```python
class DeliberationEngine:
    """
    Orchestrates multi-agent deliberation within a thread.

    Implements the core loop from docs/SYSTEM_DESIGN.md:
    1. Observer detects phase (docs/OBSERVER_SPEC.md)
    2. Trigger rules select which agents respond (docs/TRIGGER_RULES.md)
    3. Selected agents generate posts (with tool access)
    4. Energy model updates (docs/ENERGY_MODEL.md)
    5. Check termination conditions
    6. Loop until convergence
    7. Generate synthesis using output template

    This class wires together the existing spec implementations.
    It should NOT re-implement the logic described in docs/ — it should
    faithfully translate those specifications into code.
    """

    def __init__(
        self,
        observer: ObserverAgent,
        energy_calculator: EnergyCalculator,
        trigger_evaluator: TriggerEvaluator,
        synthesis_generator: SynthesisGenerator,
        cost_tracker: CostTracker,
    ):
        self.observer = observer
        self.energy = energy_calculator
        self.triggers = trigger_evaluator
        self.synthesis = synthesis_generator
        self.costs = cost_tracker

    async def run(
        self,
        thread: Thread,
        subreddit: SubredditConfig,
        memberships: List[SubredditMembership],
        agents: List[BaseAgent]
    ) -> AsyncIterator[Union[Post, PhaseTransition, Synthesis, CostUpdate]]:
        """
        Run the deliberation loop, yielding events for SSE streaming.

        Yields:
        - Post: each agent contribution
        - PhaseTransition: when observer detects phase change
        - CostUpdate: periodic cost tracking updates
        - Synthesis: final structured output

        Termination conditions (from docs/ENERGY_MODEL.md):
        - Energy drops below threshold for N consecutive rounds
        - Max turns reached
        - Cost budget exceeded
        - Human cancellation
        """

        posts: List[Post] = []
        turn = 0

        while True:
            # 1. Observer detects phase
            phase = await self.observer.detect_phase(posts, thread)
            if phase != thread.current_phase:
                thread.current_phase = phase
                yield PhaseTransition(phase=phase, turn=turn)

            # 2. Trigger rules select responding agents
            triggered_agents = await self.triggers.evaluate(
                phase=phase,
                posts=posts,
                memberships=memberships,
                agents=agents
            )

            # 3. Each triggered agent generates a post
            for membership in triggered_agents:
                agent = _find_agent(membership.agent_id, agents)

                prompt = await build_agent_prompt(
                    agent=agent,
                    membership=membership,
                    subreddit=subreddit,
                    phase=phase,
                    thread_context=ThreadContext(
                        topic=thread.title,
                        initial_post=thread.initial_post,
                        posts=posts
                    ),
                    available_tools=_get_tools(membership.tool_access)
                )

                post = await self._generate_post(agent, membership, prompt, thread)
                posts.append(post)
                yield post

                # Track cost
                self.costs.record(thread.id, post.tokens_used)
                yield CostUpdate(
                    total_tokens=self.costs.total_tokens(thread.id),
                    estimated_cost_usd=self.costs.estimated_cost(thread.id)
                )

                # Check cost budget
                if self.costs.estimated_cost(thread.id) > subreddit.max_cost_per_thread_usd:
                    thread.status = ThreadStatus.FAILED
                    yield CostUpdate(budget_exceeded=True)
                    # Still generate synthesis with what we have
                    break

            # 4. Update energy
            energy = await self.energy.calculate(posts)

            # 5. Check termination
            if self._should_terminate(energy, turn, thread):
                break

            # 6. Check for human input (if participation model allows)
            human_post = await self._check_human_input(thread)
            if human_post:
                posts.append(human_post)
                yield human_post

            turn += 1

        # 7. Generate synthesis
        synthesis = await self.synthesis.generate(
            thread=thread,
            posts=posts,
            template=subreddit.output_template
        )

        # 8. Verify citations
        synthesis.citation_verification = await self._verify_citations(synthesis)

        yield synthesis
```

### 6.3 Cost Tracking

**Build this from day one. Non-negotiable.**

```python
class CostTracker:
    """
    Track token usage and estimated cost per thread.

    Pricing is configurable. Default assumes Anthropic Claude Sonnet pricing.
    Update when models or pricing change.
    """

    def __init__(self, pricing: ModelPricing):
        self.pricing = pricing
        self._records: Dict[UUID, List[TokenRecord]] = {}

    def record(self, thread_id: UUID, tokens: int, model: str = "default"):
        """Record token usage for a thread."""
        if thread_id not in self._records:
            self._records[thread_id] = []
        self._records[thread_id].append(TokenRecord(
            tokens=tokens, model=model, timestamp=datetime.utcnow()
        ))

    def total_tokens(self, thread_id: UUID) -> int:
        return sum(r.tokens for r in self._records.get(thread_id, []))

    def estimated_cost(self, thread_id: UUID) -> float:
        """Estimate cost in USD based on current pricing."""
        total = self.total_tokens(thread_id)
        return total * self.pricing.cost_per_token

    def thread_summary(self, thread_id: UUID) -> CostSummary:
        """Summary for display and logging."""
        records = self._records.get(thread_id, [])
        return CostSummary(
            thread_id=thread_id,
            total_tokens=sum(r.tokens for r in records),
            estimated_cost_usd=self.estimated_cost(thread_id),
            num_llm_calls=len(records),
            duration_seconds=(records[-1].timestamp - records[0].timestamp).total_seconds()
                if len(records) > 1 else 0
        )


class ModelPricing(BaseModel):
    """Configurable model pricing."""
    model_name: str = "claude-sonnet-4-20250514"
    cost_per_input_token: float = 0.000003   # $3/M input tokens
    cost_per_output_token: float = 0.000015  # $15/M output tokens
    # Simplified as blended rate for tracking:
    cost_per_token: float = 0.000006  # ~$6/M blended


class CostSummary(BaseModel):
    thread_id: UUID
    total_tokens: int
    estimated_cost_usd: float
    num_llm_calls: int
    duration_seconds: float
```

### 6.4 Synthesis Generation

```python
class SynthesisGenerator:
    """
    Generate structured synthesis from deliberation posts.

    Uses the subreddit's output template to structure the final output.
    This is a separate LLM call that reads ALL posts and produces
    the structured assessment.
    """

    async def generate(
        self,
        thread: Thread,
        posts: List[Post],
        template: OutputTemplate
    ) -> Synthesis:
        """
        Generate synthesis following the output template.

        The synthesis prompt instructs the LLM to:
        1. Read all posts
        2. Produce each section from the template
        3. Cite sources for every claim (using citations from posts)
        4. Identify and include minority positions
        5. Produce metadata (confidence, evidence quality, etc.)
        6. Generate audit chains linking claims → posts → citations
        """

        section_instructions = "\n".join(
            f"### {s.name}\n{s.description}"
            for s in template.sections
        )

        prompt = f"""You are synthesizing a multi-expert deliberation into a structured assessment.

## Thread Topic
{thread.title}

## Initial Post
{thread.initial_post}

## Expert Deliberation ({len(posts)} posts)
{_format_all_posts(posts)}

## Output Template
Produce each of the following sections. Follow the instructions exactly.

{section_instructions}

## Metadata
Also produce:
{', '.join(template.metadata_fields)}

## Critical Requirements
1. Every factual claim must cite a source from the deliberation. Use [PUBMED:PMID] or [INTERNAL:id] format.
2. The "Minority Positions" section (or equivalent) must not be empty. If there was genuine consensus, explain what the strongest counter-argument was and why it was rejected.
3. Recommendations must be specific enough to act on. "Further research is needed" is not a recommendation. "Run a dose-response assay for compound X in HEK293 cells expressing the Y target" is.
4. If evidence quality is mixed, say so. Don't paper over uncertainty.
5. Produce an audit trail: for each major claim, list which expert posts supported it and which sources they cited.
"""

        result = await self._llm_generate(prompt)

        # Parse into structured sections
        sections = self._parse_sections(result, template)

        # Extract audit chains
        audit_chains = self._extract_audit_chains(result, posts)

        return Synthesis(
            id=uuid4(),
            thread_id=thread.id,
            template_type=template.template_type,
            sections=sections,
            metadata=self._extract_metadata(result, template.metadata_fields),
            audit_chains=audit_chains,
            total_citations=self._count_citations(sections),
            citation_verification=CitationVerification(
                total_citations=0, verified=0, unverified=0, flagged=0, details=[]
            ),  # Verification happens after generation
            tokens_used=0,  # Updated after LLM call
            created_at=datetime.utcnow()
        )
```

---

## 7. Human Participation

### 7.1 Human Posts

Humans can participate in deliberations based on the subreddit's participation model.

```python
class HumanPost(Post):
    """
    A human contribution to a deliberation thread.

    Human posts carry special weight:
    - All agents see them as high-priority input
    - They can redirect focus (energy boost, phase influence)
    - They can inject new data or constraints
    """

    is_human: bool = True
    human_id: UUID
    post_type: HumanPostType


class HumanPostType(str, Enum):
    COMMENT = "comment"        # General contribution
    QUESTION = "question"      # Directed question → triggers all relevant agents to respond
    DATA = "data"              # New data injection → triggers energy boost
    REDIRECT = "redirect"      # Change focus → can influence phase transition
```

### 7.2 Participation Model Enforcement

```python
async def validate_human_participation(
    subreddit: SubredditConfig,
    post_type: HumanPostType
) -> bool:
    """
    Enforce participation model rules.

    OBSERVER: No human posts allowed (read-only)
    GUIDED: QUESTION and REDIRECT only
    PARTICIPANT: All post types allowed
    APPROVER: All types, plus deliberation pauses at phase transitions
    """
    rules = {
        ParticipationModel.OBSERVER: [],
        ParticipationModel.GUIDED: [HumanPostType.QUESTION, HumanPostType.REDIRECT],
        ParticipationModel.PARTICIPANT: list(HumanPostType),
        ParticipationModel.APPROVER: list(HumanPostType),
    }
    return post_type in rules[subreddit.participation_model]
```

---

## 8. Database Schema

```sql
-- Subreddits
CREATE TABLE subreddits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    purpose JSONB NOT NULL,
    output_template JSONB NOT NULL,
    participation_model VARCHAR(20) NOT NULL,
    engine_overrides JSONB DEFAULT '{}',
    max_cost_per_thread_usd FLOAT DEFAULT 5.0,
    monthly_budget_usd FLOAT,
    created_by UUID NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Base Agents (the pool)
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type VARCHAR(100) NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    expertise_tags TEXT[] DEFAULT '{}',
    persona_prompt TEXT NOT NULL,
    phase_mandates JSONB NOT NULL,
    domain_keywords TEXT[] DEFAULT '{}',
    evaluation_criteria JSONB NOT NULL,
    is_red_team BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    version INT DEFAULT 1
);

CREATE INDEX idx_agents_expertise ON agents USING GIN (expertise_tags);
CREATE INDEX idx_agents_status ON agents(status);

-- Subreddit Memberships
CREATE TABLE subreddit_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id),
    subreddit_id UUID REFERENCES subreddits(id),
    role_prompt TEXT NOT NULL,
    tool_access TEXT[] DEFAULT '{}',
    threads_participated INT DEFAULT 0,
    total_posts INT DEFAULT 0,
    joined_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(agent_id, subreddit_id)
);

CREATE INDEX idx_memberships_subreddit ON subreddit_memberships(subreddit_id);

-- Threads
CREATE TABLE threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subreddit_id UUID REFERENCES subreddits(id) NOT NULL,
    title VARCHAR(500) NOT NULL,
    initial_post TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    current_phase VARCHAR(20) DEFAULT 'explore',
    total_posts INT DEFAULT 0,
    total_tokens_used INT DEFAULT 0,
    estimated_cost_usd FLOAT DEFAULT 0.0,
    created_by UUID NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE INDEX idx_threads_subreddit ON threads(subreddit_id);
CREATE INDEX idx_threads_status ON threads(status);

-- Posts
CREATE TABLE posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID REFERENCES threads(id) NOT NULL,
    agent_id UUID REFERENCES agents(id),     -- NULL for human posts
    is_human BOOLEAN DEFAULT FALSE,
    human_id UUID,
    human_post_type VARCHAR(20),
    phase VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    citations JSONB DEFAULT '[]',
    tool_calls JSONB DEFAULT '[]',
    tokens_used INT DEFAULT 0,
    novelty_score FLOAT,
    relevance_score FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_posts_thread ON posts(thread_id);
CREATE INDEX idx_posts_agent ON posts(agent_id);

-- Syntheses
CREATE TABLE syntheses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID REFERENCES threads(id) UNIQUE NOT NULL,
    template_type VARCHAR(50) NOT NULL,
    sections JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    audit_chains JSONB DEFAULT '[]',
    total_citations INT DEFAULT 0,
    citation_verification JSONB DEFAULT '{}',
    tokens_used INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Cost Records
CREATE TABLE cost_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID REFERENCES threads(id) NOT NULL,
    tokens INT NOT NULL,
    model VARCHAR(100) NOT NULL,
    estimated_cost_usd FLOAT NOT NULL,
    recorded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_cost_thread ON cost_records(thread_id);

-- Tool Configurations
CREATE TABLE tool_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subreddit_id UUID REFERENCES subreddits(id),
    tool_id VARCHAR(100) NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    tool_type VARCHAR(50) NOT NULL,
    connection_config JSONB DEFAULT '{}',
    enabled BOOLEAN DEFAULT TRUE,
    UNIQUE(subreddit_id, tool_id)
);
```

---

## 9. API Endpoints

```python
# ============ SUBREDDIT ENDPOINTS ============

@router.post("/api/subreddits", response_model=SubredditConfig)
async def create_subreddit(request: CreateSubredditRequest):
    """
    Create a new subreddit.
    1. Validates purpose structure
    2. Runs agent recruitment
    3. Returns config with proposed roster + any expertise gaps
    4. Human reviews before activation
    """

@router.get("/api/subreddits", response_model=List[SubredditSummary])
async def list_subreddits():
    """List all subreddits with activity stats (thread count, last active)."""

@router.get("/api/subreddits/{name}", response_model=SubredditDetail)
async def get_subreddit(name: str):
    """Get subreddit details: config, roster, recent threads."""

@router.put("/api/subreddits/{subreddit_id}/roster", response_model=SubredditConfig)
async def update_roster(subreddit_id: UUID, updates: RosterUpdate):
    """Add or remove agents from a subreddit's roster."""

@router.post("/api/subreddits/{subreddit_id}/activate")
async def activate_subreddit(subreddit_id: UUID):
    """Activate a subreddit after human review of config and roster."""


# ============ THREAD ENDPOINTS ============

@router.post("/api/subreddits/{name}/threads", response_model=Thread)
async def create_thread(name: str, request: CreateThreadRequest):
    """Create and start a new deliberation thread."""

@router.get("/api/subreddits/{name}/threads", response_model=List[ThreadSummary])
async def list_threads(name: str, status: Optional[str] = None):
    """List threads in a subreddit, optionally filtered by status."""

@router.get("/api/threads/{thread_id}", response_model=ThreadDetail)
async def get_thread(thread_id: UUID):
    """Get full thread: all posts, synthesis if complete, cost summary."""

@router.get("/api/threads/{thread_id}/stream")
async def stream_thread(thread_id: UUID):
    """SSE stream of deliberation events (posts, phase transitions, cost updates)."""

@router.post("/api/threads/{thread_id}/posts", response_model=Post)
async def create_human_post(thread_id: UUID, post: HumanPostRequest):
    """Human contributes to a thread. Validates against participation model."""

@router.post("/api/threads/{thread_id}/cancel")
async def cancel_thread(thread_id: UUID):
    """Cancel an active deliberation."""


# ============ AGENT ENDPOINTS ============

@router.get("/api/agents", response_model=List[AgentSummary])
async def list_agents(expertise: Optional[str] = None):
    """List agents in the pool, optionally filtered by expertise tag."""

@router.get("/api/agents/{agent_id}", response_model=AgentDetail)
async def get_agent(agent_id: UUID):
    """Get agent details: persona, subreddit memberships, participation stats."""


# ============ COST ENDPOINTS ============

@router.get("/api/costs/summary")
async def cost_summary(
    subreddit_id: Optional[UUID] = None,
    days: int = 30
):
    """Cost summary: total tokens, estimated cost, per-subreddit breakdown."""

@router.get("/api/threads/{thread_id}/costs", response_model=CostSummary)
async def thread_costs(thread_id: UUID):
    """Detailed cost breakdown for a specific thread."""
```

---

## 10. Implementation Plan

### Phase 1: Core Deliberation Loop (Weeks 1-3)

**Goal:** One subreddit (`target_validation`), 6 agents, human-initiated threads, PubMed tool access, structured synthesis output. End-to-end working.

```
Week 1: Foundation
  - [ ] Project scaffolding (FastAPI, PostgreSQL, project structure)
  - [ ] Pydantic models: SubredditConfig, BaseAgent, SubredditMembership, Thread, Post, Synthesis
  - [ ] Database migrations (all tables above)
  - [ ] Agent persona YAML loading
  - [ ] Write 4 core personas: molecular_biology, medicinal_chemistry, admet, red_team_general
  - [ ] Subreddit CRUD endpoints

Week 2: Engine
  - [ ] Implement Observer (translate docs/OBSERVER_SPEC.md to code)
  - [ ] Implement Energy Calculator (translate docs/ENERGY_MODEL.md)
  - [ ] Implement Trigger Evaluator (translate docs/TRIGGER_RULES.md)
  - [ ] Agent prompt assembly (build_agent_prompt)
  - [ ] PubMed tool implementation
  - [ ] Single-turn agent post generation (LLM call + tool use)
  - [ ] DeliberationEngine.run() — full loop with termination
  - [ ] Cost tracker implementation

Week 3: Synthesis and streaming
  - [ ] Synthesis generator with ASSESSMENT_TEMPLATE
  - [ ] Citation extraction from posts
  - [ ] Automated citation verification (check PMIDs exist)
  - [ ] Audit chain generation
  - [ ] SSE streaming endpoint
  - [ ] Thread CRUD endpoints
  - [ ] End-to-end test: submit hypothesis → get synthesis
```

**Phase 1 Validation Criteria:**

1. Submit "Evaluate GLP-1 receptor agonism as a therapeutic approach for Alzheimer's disease" to `r/target_validation`
2. System produces 12-25 posts across 4 phases
3. Synthesis follows ASSESSMENT_TEMPLATE structure (all 7 sections present)
4. >80% of citations in synthesis are real PubMed papers (automated check)
5. Cost tracking shows total tokens and estimated USD
6. Red team agent raises at least 2 substantive concerns
7. Deliberation completes in <15 minutes wall clock time

### Phase 2: Multi-Subreddit and Agent Pool (Weeks 4-6)

**Goal:** Three subreddit types, full agent roster, agent recruitment, human participation, different output templates.

```
Week 4: Agent roster expansion and recruitment
  - [ ] Write remaining 4 personas: clinical, regulatory, computational_biology, red_team_biology
  - [ ] Agent recruitment logic (expertise matching, gap detection)
  - [ ] Subreddit creation flow (purpose → recruit → review → activate)
  - [ ] Persona library browser (list available personas, create agents from templates)

Week 5: Multi-subreddit
  - [ ] Create literature_review subreddit type with REVIEW_TEMPLATE
  - [ ] Create novel_ideas subreddit type with IDEATION_TEMPLATE
  - [ ] Output template system (different synthesis structure per subreddit)
  - [ ] Subreddit-scoped tool access (different tools per subreddit)
  - [ ] Web search tool implementation (for novel_ideas)

Week 6: Human participation and polish
  - [ ] Human post types: comment, question, data, redirect
  - [ ] Participation model enforcement (observer, guided, participant, approver)
  - [ ] Energy injection from human posts (human question → energy boost)
  - [ ] Thread pause/resume for approver model
  - [ ] Cost dashboard endpoint
  - [ ] Integration tests across all 3 subreddit types
```

**Phase 2 Validation Criteria:**

1. Three subreddits active with appropriate agent rosters
2. Same topic submitted to different subreddits produces different output formats
3. Agent recruitment correctly identifies gaps when subreddit requires missing expertise
4. Human can inject a question mid-deliberation and agents respond to it
5. Approver model pauses deliberation at phase transitions
6. Monthly cost summary shows per-subreddit breakdown
7. Each agent has a recognizably different voice (blind test: can a reader identify which agent wrote a post based on reasoning style alone?)

---

## 11. Testing Strategy

### Unit Tests

```python
# Agent recruitment
def test_recruitment_finds_matching_agents():
    pool = [make_agent(tags=["molecular_biology", "oncology"])]
    purpose = SubredditPurpose(required_expertise=["molecular_biology"], primary_domain="oncology")
    result = await recruit_for_subreddit(purpose, pool, uuid4())
    assert len(result.memberships) == 1
    assert len(result.gaps) == 0  # Plus red team gap

def test_recruitment_reports_gaps():
    pool = [make_agent(tags=["chemistry"])]
    purpose = SubredditPurpose(required_expertise=["biostatistics"], primary_domain="general")
    result = await recruit_for_subreddit(purpose, pool, uuid4())
    assert len(result.gaps) == 1
    assert result.gaps[0].expertise == "biostatistics"

def test_recruitment_always_includes_red_team():
    purpose = SubredditPurpose(required_expertise=["biology"], primary_domain="general")
    result = await recruit_for_subreddit(purpose, [make_agent(tags=["biology"])], uuid4())
    has_red_team_gap = any(g.is_red_team for g in result.gaps)
    has_red_team_member = any(
        get_agent(m.agent_id).is_red_team for m in result.memberships
    )
    assert has_red_team_gap or has_red_team_member

# Cost tracking
def test_cost_budget_exceeded_terminates():
    tracker = CostTracker(ModelPricing(cost_per_token=0.01))  # Expensive for testing
    thread_id = uuid4()
    for _ in range(100):
        tracker.record(thread_id, 1000)
    assert tracker.estimated_cost(thread_id) > 5.0  # Over default budget

# Citation verification
def test_citation_verification_catches_fake_pmid():
    fake_citation = Citation(source_type="pubmed", source_id="99999999999", ...)
    result = await verify_citation(fake_citation)
    assert result.status == "flagged"

# Output template
def test_synthesis_covers_all_template_sections():
    sections = parse_synthesis(raw_synthesis, ASSESSMENT_TEMPLATE)
    for template_section in ASSESSMENT_TEMPLATE.sections:
        if template_section.required:
            assert template_section.name in sections

# Participation model
def test_observer_blocks_human_posts():
    subreddit = make_subreddit(participation_model=ParticipationModel.OBSERVER)
    assert not await validate_human_participation(subreddit, HumanPostType.COMMENT)

def test_guided_allows_questions():
    subreddit = make_subreddit(participation_model=ParticipationModel.GUIDED)
    assert await validate_human_participation(subreddit, HumanPostType.QUESTION)
    assert not await validate_human_participation(subreddit, HumanPostType.COMMENT)
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_full_deliberation_end_to_end():
    """Create subreddit, submit thread, get synthesis with citations."""
    subreddit = await create_and_activate_subreddit("test_validation", ThinkingType.ASSESSMENT)
    thread = await create_thread(subreddit.id, "Evaluate PCSK9 inhibition for cardiovascular disease")

    events = []
    async for event in engine.run(thread, subreddit, ...):
        events.append(event)

    posts = [e for e in events if isinstance(e, Post)]
    synthesis = next(e for e in events if isinstance(e, Synthesis))

    assert len(posts) >= 12
    assert all(s in synthesis.sections for s in ["Executive Summary", "Evidence For", "Key Risks"])
    assert synthesis.citation_verification.flagged == 0
    assert synthesis.total_citations > 0

@pytest.mark.asyncio
async def test_different_subreddits_produce_different_outputs():
    """Same topic, different subreddit types → different output structure."""
    topic = "Recent paper on CRISPR base editing efficiency improvements"

    assessment = await run_deliberation("target_validation", topic)
    review = await run_deliberation("literature_review", topic)

    assert "Executive Summary" in assessment.sections
    assert "Publication Summary" in review.sections
    assert "Executive Summary" not in review.sections

@pytest.mark.asyncio
async def test_human_question_gets_agent_response():
    """Human injects question, agents respond in next turn."""
    thread = await create_active_thread()
    await inject_human_post(thread.id, HumanPostType.QUESTION, "What about off-target effects?")
    next_posts = await get_next_round_posts(thread.id)
    content = " ".join(p.content for p in next_posts)
    assert "off-target" in content.lower()
```

---

## 12. File Structure

```
emergent-deliberation-platform/
├── docs/                               # Existing design docs — DO NOT MODIFY
│   ├── README.md
│   ├── AGENT_PROMPTS.md
│   ├── OBSERVER_SPEC.md
│   ├── TRIGGER_RULES.md
│   ├── ENERGY_MODEL.md
│   └── SYSTEM_DESIGN.md
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                     # FastAPI app entry point
│   │   ├── config.py                   # Configuration loading
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── subreddit.py            # SubredditConfig, Purpose, OutputTemplate
│   │   │   ├── agent.py                # BaseAgent, SubredditMembership
│   │   │   ├── thread.py               # Thread, Post, Synthesis
│   │   │   ├── cost.py                 # CostRecord, CostSummary, ModelPricing
│   │   │   └── enums.py                # All enums
│   │   ├── engine/
│   │   │   ├── __init__.py
│   │   │   ├── deliberation.py         # DeliberationEngine (orchestrator)
│   │   │   ├── observer.py             # From docs/OBSERVER_SPEC.md
│   │   │   ├── energy.py               # From docs/ENERGY_MODEL.md
│   │   │   ├── triggers.py             # From docs/TRIGGER_RULES.md
│   │   │   ├── synthesis.py            # SynthesisGenerator
│   │   │   └── cost_tracker.py         # CostTracker
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── prompt_builder.py       # build_agent_prompt()
│   │   │   ├── recruitment.py          # recruit_for_subreddit()
│   │   │   └── personas/               # Curated YAML persona files
│   │   │       ├── molecular_biology.yaml
│   │   │       ├── medicinal_chemistry.yaml
│   │   │       ├── admet.yaml
│   │   │       ├── clinical.yaml
│   │   │       ├── regulatory.yaml
│   │   │       ├── computational_biology.yaml
│   │   │       ├── red_team_general.yaml
│   │   │       └── red_team_biology.yaml
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── registry.py
│   │   │   ├── pubmed.py
│   │   │   ├── web_search.py
│   │   │   └── citation_verifier.py    # Automated citation checking
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── subreddits.py
│   │   │   ├── threads.py
│   │   │   ├── agents.py
│   │   │   └── costs.py
│   │   └── db/
│   │       ├── __init__.py
│   │       ├── connection.py
│   │       └── migrations/
│   │           └── 001_initial_schema.sql
│   ├── tests/
│   │   ├── unit/
│   │   │   ├── test_recruitment.py
│   │   │   ├── test_cost_tracker.py
│   │   │   ├── test_citation_verifier.py
│   │   │   ├── test_participation.py
│   │   │   └── test_output_templates.py
│   │   └── integration/
│   │       ├── test_deliberation_e2e.py
│   │       ├── test_multi_subreddit.py
│   │       └── test_human_participation.py
│   ├── config/
│   │   └── platform.yaml
│   ├── requirements.txt
│   └── Dockerfile
└── docker-compose.yml
```

---

## 13. Configuration

```yaml
# config/platform.yaml

platform:
  name: "Emergent Deliberation Platform"
  llm_model: "anthropic:claude-sonnet-4-20250514"
  synthesis_model: "anthropic:claude-sonnet-4-20250514"

subreddit_defaults:
  min_agents: 3
  max_agents: 8
  always_include_red_team: true
  participation_model: "guided"
  max_cost_per_thread_usd: 5.0

engine:
  max_turns: 30
  min_posts: 12
  energy_threshold: 0.2
  low_energy_rounds: 3

observer:
  hysteresis_threshold: 3
  window_size: 10

triggers:
  refractory_period: 2
  relevance_threshold: 2
  silence_max: 6

cost:
  model_pricing:
    model_name: "claude-sonnet-4-20250514"
    cost_per_input_token: 0.000003
    cost_per_output_token: 0.000015
    cost_per_token: 0.000006  # Blended estimate
  alert_threshold_usd: 3.0   # Warn in logs when thread exceeds this
```

---

## 14. Success Criteria

| Metric | Target | Measurement |
|---|---|---|
| Synthesis has all template sections | 100% | Automated: check section names present |
| Citations are real (not hallucinated) | >90% verified | Automated: PubMed API lookup |
| Red team raises substantive concerns | Every thread | Manual: review red team posts |
| Agents have distinct voices | Identifiable | Blind test: can reviewer identify agent by post? |
| Wall clock time per deliberation | <15 minutes | Automated: timestamp delta |
| Cost per deliberation | <$3 typical | Automated: cost tracker |
| Human question gets addressed | 100% of the time | Manual: check post-question responses |
| Different subreddits → different outputs | Templates correct | Automated: section name validation |

---

*Phase 1-2 Implementation Prompt v2.0*
*Scope: Core engine + multi-subreddit + agent pool*
*Excludes: Memory system, event-driven triggers, cross-subreddit references*
*Created: 2026-02-11*
