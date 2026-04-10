"""Core data models for the Colloquip deliberation system."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Phase(str, Enum):
    EXPLORE = "explore"
    DEBATE = "debate"
    DEEPEN = "deepen"
    CONVERGE = "converge"
    SYNTHESIS = "synthesis"


class AgentStance(str, Enum):
    SUPPORTIVE = "supportive"
    CRITICAL = "critical"
    NEUTRAL = "neutral"
    NOVEL_CONNECTION = "novel_connection"


class EnergySource(str, Enum):
    NEW_KNOWLEDGE = "new_knowledge"
    HUMAN_INTERVENTION = "human_intervention"
    NOVEL_POST = "novel_post"
    RED_TEAM_CHALLENGE = "red_team_challenge"


class SessionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class Citation(BaseModel):
    document_id: str
    title: str
    excerpt: str
    relevance: float = Field(ge=0.0, le=1.0)


class Post(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    agent_id: str
    content: str
    stance: AgentStance
    citations: List[Citation] = Field(default_factory=list)
    key_claims: List[str] = Field(default_factory=list)
    questions_raised: List[str] = Field(default_factory=list)
    connections_identified: List[str] = Field(default_factory=list)
    novelty_score: float = Field(default=0.0, ge=0.0, le=1.0)
    phase: Phase
    triggered_by: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConversationMetrics(BaseModel):
    question_rate: float = Field(ge=0.0, le=1.0)
    disagreement_rate: float = Field(ge=0.0, le=1.0)
    topic_diversity: float = Field(ge=0.0, le=1.0)
    citation_density: float = Field(ge=0.0, le=1.0)
    novelty_avg: float = Field(ge=0.0, le=1.0)
    energy: float = Field(ge=0.0, le=1.0)
    posts_since_novel: int = Field(ge=0)


class PhaseSignal(BaseModel):
    current_phase: Phase
    confidence: float = Field(ge=0.0, le=1.0)
    metrics: ConversationMetrics
    observation: Optional[str] = None


class EnergyUpdate(BaseModel):
    turn: int
    energy: float = Field(ge=0.0, le=1.0)
    components: Dict[str, float] = Field(default_factory=dict)


class DeliberationSession(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    hypothesis: str
    status: SessionStatus = SessionStatus.PENDING
    phase: Phase = Phase.EXPLORE
    config: Dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConsensusMap(BaseModel):
    session_id: UUID
    summary: str
    agreements: List[str] = Field(default_factory=list)
    disagreements: List[str] = Field(default_factory=list)
    minority_positions: List[str] = Field(default_factory=list)
    serendipity_connections: List[Dict] = Field(default_factory=list)
    final_stances: Dict[str, AgentStance] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentConfig(BaseModel):
    agent_id: str
    display_name: str
    persona_prompt: str
    phase_mandates: Dict[Phase, str]
    domain_keywords: List[str]
    knowledge_scope: List[str]
    evaluation_criteria: Dict[str, float] = Field(default_factory=dict)
    is_red_team: bool = False
    autoresearch_enabled: bool = False


class EngineConfig(BaseModel):
    max_turns: int = 30
    min_posts: int = 12
    energy_threshold: float = 0.2
    low_energy_rounds: int = 3
    refractory_period: int = 2
    hysteresis_threshold: int = 3
    phase_max_tokens: Dict[str, int] = Field(
        default_factory=lambda: {
            "explore": 1024,
            "debate": 1280,
            "deepen": 1024,
            "converge": 768,
            "synthesis": 2048,
        }
    )


class HumanIntervention(BaseModel):
    session_id: UUID
    type: Literal["question", "data", "redirect", "terminate"]
    content: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentDependencies(BaseModel):
    """Context passed to an agent when generating a post."""

    session: DeliberationSession
    phase: Phase
    phase_signal: PhaseSignal
    posts: List[Post]
    knowledge_context: List[str] = Field(default_factory=list)
    # Subreddit mission (program.md-style directive) injected into system prompt
    subreddit_mission: Optional[str] = None
    mission_objectives: List["MissionObjective"] = Field(default_factory=list)
    # Optional autoresearch findings appended to user prompt
    autoresearch_findings: Optional[str] = None
    autoresearch_citations: List[Citation] = Field(default_factory=list)
    # Subreddit id (for downstream budget/membership lookups)
    subreddit_id: Optional[UUID] = None

    model_config = {"arbitrary_types_allowed": True}

    def with_findings(
        self,
        findings: str,
        citations: Optional[List[Citation]] = None,
    ) -> "AgentDependencies":
        """Return a shallow copy with autoresearch findings attached."""
        return self.model_copy(
            update={
                "autoresearch_findings": findings,
                "autoresearch_citations": citations or [],
            }
        )


# ---------------------------------------------------------------------------
# New enums for the social platform
# ---------------------------------------------------------------------------


class ThinkingType(str, Enum):
    ASSESSMENT = "assessment"
    ANALYSIS = "analysis"
    REVIEW = "review"
    IDEATION = "ideation"


class ParticipationModel(str, Enum):
    OBSERVER = "observer"
    GUIDED = "guided"
    PARTICIPANT = "participant"
    APPROVER = "approver"


class SubredditRole(str, Enum):
    MEMBER = "member"
    MODERATOR = "moderator"
    RED_TEAM = "red_team"


class AgentStatus(str, Enum):
    ACTIVE = "active"
    RETIRED = "retired"
    DRAFT = "draft"


class HumanPostType(str, Enum):
    COMMENT = "comment"
    QUESTION = "question"
    DATA = "data"
    REDIRECT = "redirect"


class ThreadStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ToolType(str, Enum):
    LITERATURE_SEARCH = "literature_search"
    INTERNAL_DATABASE = "internal_database"
    WEB_SEARCH = "web_search"
    COMPUTATION = "computation"


# ---------------------------------------------------------------------------
# New models for the social platform
# ---------------------------------------------------------------------------


class OutputSection(BaseModel):
    """A section in an output template."""

    name: str
    description: str
    required: bool = True


class OutputTemplate(BaseModel):
    """Structured synthesis format for a subreddit."""

    template_type: str
    sections: List[OutputSection]
    metadata_fields: List[str] = Field(default_factory=list)


class SubredditPurpose(BaseModel):
    """Structured purpose definition for a subreddit."""

    thinking_type: ThinkingType
    core_questions: List[str]
    decision_context: str
    primary_domain: str
    secondary_domains: List[str] = Field(default_factory=list)
    required_expertise: List[str] = Field(default_factory=list)
    optional_expertise: List[str] = Field(default_factory=list)


class ToolConfig(BaseModel):
    """A tool available within a subreddit."""

    tool_id: str
    display_name: str
    description: str
    tool_type: ToolType
    connection_config: Dict = Field(default_factory=dict)
    enabled: bool = True


class SubredditConfig(BaseModel):
    """Complete configuration for a subreddit."""

    model_config = {"arbitrary_types_allowed": True}

    id: UUID = Field(default_factory=uuid4)
    name: str
    display_name: str
    description: str
    purpose: SubredditPurpose
    agent_roster: List["SubredditMembership"] = Field(default_factory=list)
    min_agents: int = 3
    max_agents: int = 8
    always_include_red_team: bool = True
    tool_configs: List[ToolConfig] = Field(default_factory=list)
    output_template: OutputTemplate
    participation_model: ParticipationModel = ParticipationModel.GUIDED
    engine_overrides: Optional[Dict] = None
    max_cost_per_thread_usd: float = 5.0
    monthly_budget_usd: Optional[float] = None
    created_by: Optional[UUID] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BaseAgentIdentity(BaseModel):
    """Persistent agent identity in the global pool."""

    id: UUID = Field(default_factory=uuid4)
    agent_type: str
    display_name: str
    expertise_tags: List[str] = Field(default_factory=list)
    persona_prompt: str
    phase_mandates: Dict[str, str] = Field(default_factory=dict)
    domain_keywords: List[str] = Field(default_factory=list)
    knowledge_scope: List[str] = Field(default_factory=list)
    evaluation_criteria: Dict[str, float] = Field(default_factory=dict)
    is_red_team: bool = False
    autoresearch_enabled: bool = False
    status: AgentStatus = AgentStatus.ACTIVE
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SubredditMembership(BaseModel):
    """An agent's scoped identity within a subreddit."""

    id: UUID = Field(default_factory=uuid4)
    agent_id: UUID
    subreddit_id: UUID
    role: SubredditRole = SubredditRole.MEMBER
    role_prompt: str = ""
    tool_access: List[str] = Field(default_factory=list)
    threads_participated: int = 0
    total_posts: int = 0
    # Per-agent budget & cost accounting (Phase 6)
    max_cost_per_thread_usd: Optional[float] = None
    monthly_budget_usd: Optional[float] = None
    lifetime_cost_usd: float = 0.0
    lifetime_input_tokens: int = 0
    lifetime_output_tokens: int = 0
    current_month_cost_usd: float = 0.0
    current_month_reset_at: Optional[datetime] = None
    # Org chart delegation (Phase 6)
    reports_to_agent_id: Optional[UUID] = None
    # Autoresearch policy override (Phase 6)
    autoresearch_policy: Optional[Dict[str, Any]] = None
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ModelPricing(BaseModel):
    """Configurable model pricing."""

    model_name: str = "claude-opus-4-6"
    cost_per_input_token: float = 0.000005
    cost_per_output_token: float = 0.000025
    cost_per_token: float = 0.00001


class CostRecord(BaseModel):
    """A single token usage record."""

    id: UUID = Field(default_factory=uuid4)
    thread_id: UUID
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = "default"
    estimated_cost_usd: float = 0.0
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CostSummary(BaseModel):
    """Cost summary for a thread."""

    thread_id: UUID
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    num_llm_calls: int = 0
    duration_seconds: float = 0.0


class MemoryAnnotationType(str, Enum):
    """Types of human corrections to stored memories."""

    OUTDATED = "outdated"
    CORRECTION = "correction"
    CONFIRMED = "confirmed"
    CONTEXT = "context"


class MemoryAnnotation(BaseModel):
    """A human annotation on a stored synthesis memory."""

    id: UUID = Field(default_factory=uuid4)
    memory_id: UUID
    annotation_type: MemoryAnnotationType
    content: str
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Phase 3b: Typed Memory Models (reserved for future use after calibration)
# ---------------------------------------------------------------------------


class MemoryType(str, Enum):
    """Types of decomposed memories (Phase 3b)."""

    FACTUAL = "factual"  # Verified facts, data points
    METHODOLOGICAL = "methodological"  # Approaches, techniques that worked/failed
    POSITIONAL = "positional"  # Agent stances, opinions with reasoning
    RELATIONAL = "relational"  # Connections between entities/concepts
    CONTEXTUAL = "contextual"  # Background, constraints, assumptions


class MemoryScope(str, Enum):
    """Scope of a typed memory."""

    GLOBAL = "global"  # Applicable across all subreddits
    ARENA = "arena"  # Specific to one subreddit


class TypedMemory(BaseModel):
    """A decomposed memory unit (Phase 3b).

    Not yet populated — requires calibration against 50+ synthesis memories
    to validate extraction quality > 85%.
    """

    id: UUID = Field(default_factory=uuid4)
    source_memory_id: UUID
    memory_type: MemoryType
    scope: MemoryScope
    content: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    entities: List[str] = Field(default_factory=list)
    subreddit_id: UUID
    embedding: List[float] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditChain(BaseModel):
    """Traceability chain for a claim in the synthesis."""

    claim: str
    supporting_post_ids: List[UUID] = Field(default_factory=list)
    citations: List["StructuredCitation"] = Field(default_factory=list)
    evidence_type: str = "direct"
    dissenting_agents: List[str] = Field(default_factory=list)


class CitationVerification(BaseModel):
    """Results of automated citation checking."""

    total_citations: int = 0
    verified: int = 0
    unverified: int = 0
    flagged: int = 0
    details: List[Dict] = Field(default_factory=list)


class StructuredCitation(BaseModel):
    """Enhanced citation with source tracking."""

    source_type: str = ""  # "pubmed", "internal", "web"
    source_id: str = ""  # PMID, record ID, URL
    title: str = ""
    authors: Optional[str] = None
    year: Optional[int] = None
    journal: Optional[str] = None
    snippet: str = ""
    url: Optional[str] = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Synthesis(BaseModel):
    """Structured output from a completed deliberation."""

    id: UUID = Field(default_factory=uuid4)
    thread_id: UUID
    template_type: str
    sections: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict = Field(default_factory=dict)
    audit_chains: List[AuditChain] = Field(default_factory=list)
    total_citations: int = 0
    citation_verification: CitationVerification = Field(default_factory=CitationVerification)
    tokens_used: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Thread(BaseModel):
    """A deliberation thread within a subreddit."""

    id: UUID = Field(default_factory=uuid4)
    subreddit_id: UUID
    title: str
    initial_post: str
    status: ThreadStatus = ThreadStatus.ACTIVE
    created_by: Optional[UUID] = None
    current_phase: Phase = Phase.EXPLORE
    total_posts: int = 0
    total_tokens_used: int = 0
    estimated_cost_usd: float = 0.0
    synthesis: Optional[Synthesis] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


class ExpertiseGap(BaseModel):
    """Missing expertise in a subreddit roster."""

    expertise: str
    domain: str = ""
    is_red_team: bool = False
    has_curated_template: bool = False


class RecruitmentResult(BaseModel):
    """Result of agent recruitment for a subreddit."""

    memberships: List[SubredditMembership] = Field(default_factory=list)
    gaps: List[ExpertiseGap] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase 4: Event-Driven Trigger Models
# ---------------------------------------------------------------------------


class WatcherType(str, Enum):
    """Types of event watchers."""

    LITERATURE = "literature"  # PubMed / literature DB monitoring
    SCHEDULED = "scheduled"  # Time-based triggers (cron-like)
    WEBHOOK = "webhook"  # External event ingestion


class TriageSignal(str, Enum):
    """Signal levels from triage evaluation."""

    LOW = "low"  # Log only, no action
    MEDIUM = "medium"  # Notify humans
    HIGH = "high"  # Notify + suggest immediate thread creation


class WatcherSource(BaseModel):
    """Source of a watcher event."""

    source_type: str  # "pubmed", "schedule", "webhook", etc.
    source_id: str = ""  # PMID, schedule ID, webhook sender
    url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WatcherConfig(BaseModel):
    """Configuration for a watcher instance."""

    id: UUID = Field(default_factory=uuid4)
    watcher_type: WatcherType
    subreddit_id: UUID
    name: str
    description: str = ""
    query: str = ""  # Search query for literature watchers
    poll_interval_seconds: int = 300  # Polling interval
    enabled: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)  # Type-specific config
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WatcherEvent(BaseModel):
    """An event detected by a watcher."""

    id: UUID = Field(default_factory=uuid4)
    watcher_id: UUID
    subreddit_id: UUID
    title: str
    summary: str
    source: WatcherSource
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TriageDecision(BaseModel):
    """Result of triage evaluation for a watcher event."""

    event_id: UUID
    signal: TriageSignal
    novelty: float = Field(default=0.0, ge=0.0, le=1.0)
    relevance: float = Field(default=0.0, ge=0.0, le=1.0)
    urgency: float = Field(default=0.0, ge=0.0, le=1.0)
    reasoning: str = ""
    suggested_hypothesis: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class NotificationStatus(str, Enum):
    """Status of a notification."""

    PENDING = "pending"
    READ = "read"
    ACTED = "acted"
    DISMISSED = "dismissed"


class NotificationAction(str, Enum):
    """Actions a user can take on a notification."""

    CREATE_THREAD = "create_thread"
    DISMISS = "dismiss"
    SNOOZE = "snooze"


class Notification(BaseModel):
    """A notification generated from a triage decision."""

    id: UUID = Field(default_factory=uuid4)
    watcher_id: UUID
    event_id: UUID
    subreddit_id: UUID
    title: str
    summary: str
    signal: TriageSignal
    suggested_hypothesis: Optional[str] = None
    status: NotificationStatus = NotificationStatus.PENDING
    action_taken: Optional[NotificationAction] = None
    thread_id: Optional[UUID] = None  # If a thread was created from this
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    acted_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Phase 6: Agent organization, mission, budgets, approvals, autoresearch
# ---------------------------------------------------------------------------


class MissionObjective(BaseModel):
    """A structured objective parsed from a subreddit mission markdown directive.

    Inspired by Karpathy's autoresearch program.md — humans write a markdown
    directive; objectives are extracted as H2 headings with optional metric/target
    bullets. Objectives without a metric are tracked qualitatively.
    """

    id: str
    title: str
    description: str = ""
    metric: Optional[str] = None
    target: Optional[float] = None
    status: Literal["open", "in_progress", "met", "not_met"] = "open"


class ObjectiveProgress(BaseModel):
    """Measured progress for a single mission objective."""

    objective_id: str
    title: str
    metric: Optional[str] = None
    target: Optional[float] = None
    measured_value: Optional[float] = None
    status: Literal["open", "in_progress", "met", "not_met"] = "open"
    qualitative: bool = False
    sample_size: int = 0
    detail: str = ""


class SubredditMission(BaseModel):
    """Subreddit-level mission directive and parsed objectives."""

    subreddit_id: UUID
    mission_md: Optional[str] = None
    objectives: List[MissionObjective] = Field(default_factory=list)
    version: int = 1
    updated_at: Optional[datetime] = None


class AgentBudgetSkipped(BaseModel):
    """Yieldable event: an agent was skipped because of a budget breach."""

    session_id: UUID
    agent_id: str
    turn: int
    reason: Literal["thread_budget", "agent_thread_budget", "agent_monthly_budget"]
    message: str
    estimated_cost_usd: float
    max_usd: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentCostSummary(BaseModel):
    """Per-agent cost breakdown for a thread."""

    thread_id: UUID
    agent_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    num_llm_calls: int = 0


class ApprovalRequestType(str, Enum):
    THREAD_SPAWN = "thread_spawn"
    TOOL_CALL = "tool_call"
    BUDGET_OVERRIDE = "budget_override"
    AUTORESEARCH_RUN = "autoresearch_run"
    AGENT_HIRE = "agent_hire"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


class ApprovalRequest(BaseModel):
    """A Paperclip-style human-in-loop approval request."""

    id: UUID = Field(default_factory=uuid4)
    subreddit_id: UUID
    request_type: ApprovalRequestType
    initiator: str = ""  # e.g. "watcher:<id>", "agent:<id>", "system"
    target_ref: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: ApprovalStatus = ApprovalStatus.PENDING
    reason: str = ""
    estimated_cost_usd: float = 0.0
    ttl_seconds: Optional[int] = None
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    decided_at: Optional[datetime] = None
    decided_by: Optional[str] = None


class AutoresearchActionType(str, Enum):
    SEARCH_PUBMED = "search_pubmed"
    SEARCH_WEB = "search_web"
    QUERY_COMPANY_DOCS = "query_company_docs"
    READ_MEMORY = "read_memory"
    REFLECT = "reflect"


class AutoresearchStep(BaseModel):
    """A single step in an autoresearch iteration loop."""

    step_index: int
    action: AutoresearchActionType
    rationale: str = ""
    query: str = ""
    metric_before: float = 0.0
    metric_after: float = 0.0
    delta: float = 0.0
    committed: bool = False
    tokens_in: int = 0
    tokens_out: int = 0
    summary: str = ""
    error: Optional[str] = None


class AutoresearchConfig(BaseModel):
    """Fixed-budget configuration for an autoresearch run.

    Modeled after Karpathy's autoresearch wall-clock/step budget pattern.
    """

    max_steps: int = 5
    max_tokens: int = 4000
    max_wallclock_seconds: float = 60.0
    metric: str = "novelty_gain"
    threshold: float = 0.0
    allowed_actions: List[AutoresearchActionType] = Field(
        default_factory=lambda: [
            AutoresearchActionType.SEARCH_PUBMED,
            AutoresearchActionType.SEARCH_WEB,
            AutoresearchActionType.READ_MEMORY,
            AutoresearchActionType.REFLECT,
        ]
    )


class AutoresearchStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    BUDGET_EXCEEDED = "budget_exceeded"
    FAILED = "failed"


class AutoresearchRun(BaseModel):
    """Audit record of a single autoresearch loop execution."""

    id: UUID = Field(default_factory=uuid4)
    thread_id: UUID
    agent_id: str
    subreddit_id: Optional[UUID] = None
    config: AutoresearchConfig = Field(default_factory=AutoresearchConfig)
    scratchpad: str = ""
    steps: List[AutoresearchStep] = Field(default_factory=list)
    metric_name: str = "novelty_gain"
    metric_start: float = 0.0
    metric_end: float = 0.0
    status: AutoresearchStatus = AutoresearchStatus.RUNNING
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    citations: List[Citation] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None


class OrgChartNode(BaseModel):
    agent_id: str
    display_name: str
    role: SubredditRole
    reports_to: Optional[str] = None
    post_count: int = 0
    lifetime_cost_usd: float = 0.0
    is_red_team: bool = False


class OrgChartEdge(BaseModel):
    from_agent_id: str
    to_agent_id: str
    edge_type: Literal["reports_to", "triggered"]
    weight: float = 1.0


class OrgChart(BaseModel):
    subreddit_id: UUID
    nodes: List[OrgChartNode] = Field(default_factory=list)
    edges: List[OrgChartEdge] = Field(default_factory=list)


# Hard cap to prevent runaway cost regardless of misconfigured budgets
MAX_AUTORESEARCH_TOKENS_PER_RUN = 8000


# Resolve forward references for models that use them
SubredditConfig.model_rebuild()
AgentDependencies.model_rebuild()
