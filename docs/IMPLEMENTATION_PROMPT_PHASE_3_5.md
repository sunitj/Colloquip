# Emergent Deliberation Platform: Future Phases
# Phase 3-5 — Memory, Event-Driven Triggers, Feedback Loops

## Prerequisites

**Do not begin this work until Phase 1-2 is complete and validated.** Specifically:

1. Scientists have used the platform for **at least 20 deliberations** across multiple subreddits
2. Cost per deliberation is stable and predictable (<$3 typical)
3. Citation verification rate is >90%
4. Agent voices are demonstrably distinct (validated by blind review)
5. You have real usage data: which subreddits are most active, what kinds of hypotheses are submitted, where agents produce the most/least value

This data is essential. The designs below contain parameters (decay rates, similarity thresholds, triage criteria) that **cannot be set correctly without empirical data from real usage.** Phase 1-2 generates that data.

---

## Phase 3: Institutional Memory (Weeks 7-12)

### 3.1 Design Philosophy: Start With RAG, Not Typed Memories

The original design specified five memory types (factual, methodological, positional, relational, contextual) with confidence decay, contradiction detection, and verification status. That system is the end goal, but building it before you have usage data will produce poorly calibrated parameters.

**Phase 3 starts with simple synthesis-level RAG:**

```
After each deliberation completes:
  1. Store the full Synthesis as a "memory document"
  2. Embed it (pgvector)
  3. Tag it with: subreddit, thread topic, agents involved, citations used, date

Before each new deliberation:
  1. Embed the new thread topic
  2. Retrieve top-k similar past syntheses from the same subreddit (arena-scoped)
  3. Retrieve top-k similar past syntheses from all subreddits (global)
  4. Inject as "Prior Deliberations" context in agent prompts
```

This gives agents the ability to reference what the platform has concluded before — the core value of institutional memory — without the complexity of typed memory extraction, confidence scoring, or decay functions.

### 3.2 Synthesis-Level Memory Store

```python
class SynthesisMemory(BaseModel):
    """
    A stored synthesis available for retrieval in future deliberations.

    This is the Phase 3 memory unit. It's the full synthesis, not decomposed
    into typed memories. Decomposition comes in Phase 3b after we have data
    to calibrate extraction quality.
    """

    id: UUID
    thread_id: UUID
    subreddit_id: UUID
    subreddit_name: str

    # Content
    topic: str                    # Thread title/hypothesis
    synthesis_content: str        # Full synthesis text
    key_conclusions: List[str]    # Top 3-5 conclusions extracted at save time
    citations_used: List[str]     # PMIDs and other references

    # Metadata for filtering
    agents_involved: List[str]    # Agent types that participated
    template_type: str            # assessment, review, analysis_plan, ideation
    confidence_level: str         # From synthesis metadata
    evidence_quality: str         # From synthesis metadata

    # Embedding for similarity search
    embedding: List[float]        # 1536-dim embedding of topic + key_conclusions

    created_at: datetime


class MemoryRetriever:
    """Retrieve relevant past deliberations for a new thread."""

    async def retrieve(
        self,
        topic: str,
        subreddit_id: UUID,
        max_arena: int = 3,   # Past deliberations from same subreddit
        max_global: int = 2,  # Past deliberations from any subreddit
    ) -> RetrievedMemories:
        """
        Retrieve relevant past syntheses.

        Strategy:
        1. Embed the new topic
        2. Cosine similarity search against synthesis memories
        3. Arena-scoped: same subreddit, sorted by relevance
        4. Global: all subreddits, sorted by relevance, exclude same subreddit
        5. Return top-k of each
        """

        topic_embedding = await embed(topic)

        arena = await self._query(
            embedding=topic_embedding,
            subreddit_id=subreddit_id,
            limit=max_arena
        )

        global_results = await self._query(
            embedding=topic_embedding,
            subreddit_id=None,  # All subreddits
            exclude_subreddit=subreddit_id,
            limit=max_global
        )

        return RetrievedMemories(arena=arena, global_results=global_results)


class RetrievedMemories(BaseModel):
    arena: List[SynthesisMemory]
    global_results: List[SynthesisMemory]

    def format_for_prompt(self) -> str:
        """Format retrieved memories for injection into agent prompt."""
        sections = []

        if self.arena:
            sections.append("## Relevant Past Deliberations (This Subreddit)")
            for mem in self.arena:
                sections.append(f"### {mem.topic} ({mem.created_at.strftime('%Y-%m-%d')})")
                sections.append(f"Confidence: {mem.confidence_level}")
                sections.append("Key conclusions:")
                for c in mem.key_conclusions:
                    sections.append(f"- {c}")
                sections.append("")

        if self.global_results:
            sections.append("## Related Deliberations (Other Subreddits)")
            for mem in self.global_results:
                sections.append(
                    f"### [{mem.subreddit_name}] {mem.topic} ({mem.created_at.strftime('%Y-%m-%d')})"
                )
                sections.append(f"Key conclusions:")
                for c in mem.key_conclusions:
                    sections.append(f"- {c}")
                sections.append("")

        if not sections:
            return "## Prior Deliberations\nNo relevant past deliberations found."

        return "\n".join(sections)
```

### 3.3 Prompt Integration

Add the retrieved memories as a new layer in `build_agent_prompt()`:

```python
async def build_agent_prompt(
    agent, membership, subreddit, phase, thread_context, available_tools,
    memory_retriever: Optional[MemoryRetriever] = None  # New in Phase 3
) -> str:

    # ... existing layers 1-5 ...

    # Layer 6: Prior deliberations (Phase 3)
    prior_context = ""
    if memory_retriever:
        memories = await memory_retriever.retrieve(
            topic=thread_context.topic,
            subreddit_id=subreddit.id
        )
        prior_context = memories.format_for_prompt()

    prompt = f"""{agent.persona_prompt}

## Your Role in r/{subreddit.name}
{membership.role_prompt}

{prior_context}

## Important: Using Prior Deliberations
- Reference prior conclusions when relevant: "In a previous assessment of [topic], this panel concluded..."
- If the current hypothesis contradicts a prior conclusion, flag the contradiction explicitly
- Do NOT repeat analysis that was already done — build on it
- Prior conclusions may be outdated. Check if new evidence has emerged.

... rest of prompt ...
"""
```

### 3.4 Phase 3b: Typed Memory Extraction (After Calibration)

**Only begin this after you have 50+ stored synthesis memories and can empirically measure extraction quality.**

Once you have enough data, implement the typed memory system:

```python
class TypedMemory(BaseModel):
    """
    Decomposed memory unit, extracted from syntheses.

    Phase 3b — only implement after calibrating extraction quality
    against 50+ stored syntheses.
    """

    id: UUID
    agent_id: UUID
    memory_type: MemoryType  # factual, methodological, positional, relational, contextual
    scope: MemoryScope       # global, arena

    content: str
    source_synthesis_id: UUID
    citations: List[str]

    confidence: float
    verification_status: str  # unverified, confirmed, contradicted, human_corrected

    embedding: List[float]
    created_at: datetime
    last_accessed: datetime
    expires_at: Optional[datetime]


class MemoryType(str, Enum):
    FACTUAL = "factual"
    # "Compound X showed IC50 of 5nM against target Y in HEK293 assay [INTERNAL:assay-2024-0142]"

    METHODOLOGICAL = "methodological"
    # "PK predictions from rat models underestimate human clearance by 2-3x for this compound class"

    POSITIONAL = "positional"
    # "I assessed target Z as high-risk due to cardiac liability evidence from [PUBMED:12345678]"

    RELATIONAL = "relational"
    # "Chemistry agent's SAR predictions for scaffold class A were validated in 3/5 subsequent programs"

    CONTEXTUAL = "contextual"
    # "r/target_validation typically evaluates targets at the genetic validation stage"
```

**Calibration process for typed extraction:**

1. Take 20 existing synthesis memories
2. Run the extraction LLM prompt on each → produces typed memories
3. Have a human scientist evaluate: Is each extracted memory accurate? Specific enough? Properly typed?
4. Measure extraction precision (% of extracted memories that are correct)
5. Target: >85% precision before shipping typed extraction to production
6. If <85%: iterate on the extraction prompt until quality is sufficient

**Confidence decay calibration:**

1. Take factual memories from early deliberations (>1 month old)
2. Check: is the underlying fact still accurate? Has the cited paper been retracted? Has internal data been updated?
3. Measure the natural "staleness rate" by memory type
4. Set decay rates based on observed staleness, not theoretical estimates
5. The original design proposed factual decay of 0.002/day. This may be way too fast or too slow. Let the data decide.

### 3.5 Human Memory Corrections

Even in Phase 3a (synthesis-level RAG), humans need the ability to annotate or correct stored memories:

```python
@router.post("/api/memories/{memory_id}/annotate")
async def annotate_memory(memory_id: UUID, annotation: MemoryAnnotation):
    """
    Human annotates a stored synthesis memory.

    Types:
    - OUTDATED: "This conclusion is no longer valid because..."
    - CORRECTION: "The conclusion should be X, not Y, because..."
    - CONFIRMED: "Our subsequent experiments confirmed this"
    - CONTEXT: "This is only true for cell line X, not broadly applicable"
    """

class MemoryAnnotation(BaseModel):
    annotation_type: str  # outdated, correction, confirmed, context
    content: str
    annotated_by: UUID
    created_at: datetime
```

When a memory has an annotation, include the annotation in the prompt alongside the memory. Let agents weigh the original conclusion against the human correction.

### 3.6 Database Additions (Phase 3)

```sql
-- Synthesis memories (Phase 3a)
CREATE TABLE synthesis_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID REFERENCES threads(id) UNIQUE NOT NULL,
    subreddit_id UUID REFERENCES subreddits(id) NOT NULL,
    subreddit_name VARCHAR(100) NOT NULL,
    topic TEXT NOT NULL,
    synthesis_content TEXT NOT NULL,
    key_conclusions JSONB NOT NULL,
    citations_used TEXT[] DEFAULT '{}',
    agents_involved TEXT[] DEFAULT '{}',
    template_type VARCHAR(50) NOT NULL,
    confidence_level VARCHAR(20),
    evidence_quality VARCHAR(20),
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_synth_mem_subreddit ON synthesis_memories(subreddit_id);
CREATE INDEX idx_synth_mem_embedding ON synthesis_memories
    USING ivfflat (embedding vector_cosine_ops);

-- Memory annotations (Phase 3a)
CREATE TABLE memory_annotations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id UUID REFERENCES synthesis_memories(id) NOT NULL,
    annotation_type VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    annotated_by UUID NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Typed memories (Phase 3b — only create when calibrated)
CREATE TABLE typed_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id),
    memory_type VARCHAR(20) NOT NULL,
    scope VARCHAR(20) NOT NULL,
    subreddit_id UUID REFERENCES subreddits(id),
    content TEXT NOT NULL,
    source_synthesis_id UUID REFERENCES synthesis_memories(id),
    citations TEXT[] DEFAULT '{}',
    confidence FLOAT NOT NULL,
    verification_status VARCHAR(20) DEFAULT 'unverified',
    times_referenced INT DEFAULT 0,
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT NOW(),
    last_accessed TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);

CREATE INDEX idx_typed_mem_agent ON typed_memories(agent_id);
CREATE INDEX idx_typed_mem_embedding ON typed_memories
    USING ivfflat (embedding vector_cosine_ops);
```

### 3.7 Phase 3 Validation Criteria

**Phase 3a (synthesis RAG):**
- Run 5 deliberations on related topics in the same subreddit
- The 5th deliberation's posts reference conclusions from earlier deliberations
- Synthesis for the 5th deliberation explicitly builds on (doesn't repeat) prior conclusions
- A human scientist confirms the references are accurate and add value

**Phase 3b (typed memories):**
- Memory extraction precision >85% (human-evaluated on 20 syntheses)
- Confidence decay rates calibrated against observed staleness rates
- Contradiction detection correctly identifies when new evidence conflicts with stored memory (test with deliberate contradictions)

---

## Phase 4: Event-Driven Triggers (Weeks 13-16)

### 4.1 Design Philosophy: Notification-First, Not Auto-Deliberation

Based on the practicality assessment: event-driven triggers should start as a notification and triage system, not auto-deliberation. The cost and quality risks of unsupervised deliberation are too high until the triage layer is empirically validated.

**Flow:**

```
Watcher detects event
    │
    ▼
Triage Agent evaluates (single LLM call, fast and cheap)
    │
    ├── LOW SIGNAL → Log, no action
    ├── MEDIUM SIGNAL → Notify human with triage summary
    └── HIGH SIGNAL → Notify human with triage summary + "Recommended: start deliberation"
    │
    ▼
Human decides whether to create a thread
    │
    ▼
(Only after triage validation): Enable auto-deliberation for specific, proven triggers
```

Auto-deliberation is earned, not default. A specific trigger condition must demonstrate >70% useful output rate (human-evaluated) before it's allowed to auto-create threads.

### 4.2 Watcher System

```python
class WatcherConfig(BaseModel):
    id: UUID
    subreddit_id: UUID
    watcher_type: WatcherType
    display_name: str
    description: str           # Human-readable: what this watches and why

    # Source
    source: WatcherSource

    # Trigger conditions
    trigger_condition: str     # Human-readable description
    filter_expression: Optional[str]  # Programmatic filter (regex, SQL-like, etc.)

    # Behavior
    auto_create_thread: bool = False  # DEFAULT FALSE. Earned, not default.
    auto_thread_approval_rate: Optional[float] = None  # Set after validation
    notification_targets: List[UUID]  # Humans who get notified
    triage_prompt: Optional[str] = None  # Custom triage instructions

    enabled: bool = True
    created_at: datetime


class WatcherType(str, Enum):
    FILE_SYSTEM = "file_system"     # New files in S3 path
    DATABASE = "database"           # Record changes in external database
    LITERATURE = "literature"       # New PubMed publications matching keywords
    SCHEDULED = "scheduled"         # Time-based (weekly review, monthly summary)
    WEBHOOK = "webhook"             # External system calls our API


class WatcherSource(BaseModel):
    source_type: WatcherType
    connection_string: str         # S3 path, database URL, PubMed query, etc.
    poll_interval_seconds: int = 300  # 5 minutes default
    credentials_ref: Optional[str] = None
```

### 4.3 Triage Agent

The triage agent is deliberately simple and cheap — a single LLM call that decides whether a detected event is worth human attention.

```python
class TriageAgent:
    """
    Lightweight event evaluation. Single LLM call.

    Design constraints:
    - Must be fast (<5 seconds)
    - Must be cheap (<$0.01 per evaluation)
    - Must be conservative (better to miss a low-signal event than waste resources)
    - Must produce a concise human-readable summary
    """

    async def evaluate(
        self,
        event: WatcherEvent,
        subreddit: SubredditConfig,
        recent_threads: List[ThreadSummary]  # Last 10 threads for dedup
    ) -> TriageDecision:

        prompt = f"""You are a triage agent for r/{subreddit.name}.

Subreddit purpose: {subreddit.description}
Core questions: {'; '.join(subreddit.purpose.core_questions)}

An event was detected:
Type: {event.event_type}
Source: {event.source}
Details: {event.details}

Recent threads in this subreddit (for deduplication):
{_format_recent_threads(recent_threads)}

Evaluate:
1. NOVELTY: Is this genuinely new information, or does it overlap with a recent thread?
2. RELEVANCE: Does this event relate to this subreddit's core questions?
3. SIGNAL STRENGTH: Is there enough substance here for a full expert panel deliberation?
4. URGENCY: Does this need immediate attention or can it wait?

Respond with:
- signal: low | medium | high
- summary: 2-3 sentence explanation for the human reviewer
- suggested_thread_title: if medium or high signal
- related_existing_threads: IDs of overlapping recent threads, if any
- reason_if_low: brief explanation if recommending no action
"""

        result = await self._llm_call(prompt, max_tokens=500)
        return self._parse_decision(result)


class TriageDecision(BaseModel):
    signal: str              # low, medium, high
    summary: str             # Human-readable explanation
    suggested_thread_title: Optional[str]
    related_existing_threads: List[UUID]
    reason_if_low: Optional[str]
    tokens_used: int
    evaluated_at: datetime
```

### 4.4 Watcher Implementations

```python
class LiteratureWatcher:
    """
    Watch PubMed for new publications matching keywords.

    Configuration:
    - keywords: PubMed search query
    - poll_interval: how often to check (default: daily)
    - min_relevance: minimum number of keyword matches to trigger
    """

    async def poll(self) -> List[WatcherEvent]:
        """
        Search PubMed for papers published since last check.
        Return events for papers that match the configured query.
        """
        ...


class FileSystemWatcher:
    """
    Watch an S3 path for new files.

    Configuration:
    - s3_path: bucket/prefix to watch
    - file_patterns: glob patterns to match (e.g. "*.fastq.gz", "*.csv")
    - poll_interval: how often to check
    """

    async def poll(self) -> List[WatcherEvent]:
        """List new objects in S3 path since last check."""
        ...


class ScheduledWatcher:
    """
    Time-based triggers. No external source — fires on schedule.

    Use cases:
    - Weekly literature review: "Every Monday, search for new papers on [topic]"
    - Monthly competitive landscape: "Every month, assess competitive activity in [space]"
    """

    async def check_schedule(self) -> Optional[WatcherEvent]:
        """Check if it's time to fire."""
        ...


class WebhookWatcher:
    """
    External systems call our API to trigger events.

    Use cases:
    - LIMS system notifies when new assay results are available
    - Airtable automation fires when a record status changes
    - CI/CD pipeline notifies when new analysis pipeline completes
    """

    # This is an API endpoint, not a poller
    @router.post("/api/webhooks/{watcher_id}")
    async def receive_webhook(watcher_id: UUID, payload: Dict):
        ...
```

### 4.5 Notification System

```python
class NotificationManager:
    """
    Notify humans when watchers detect events.

    Phase 4 supports:
    - In-platform notifications (poll-based, shown in UI)
    - Email notifications (optional, configurable per watcher)

    Future:
    - Slack integration
    - Push notifications
    """

    async def notify(
        self,
        watcher: WatcherConfig,
        triage: TriageDecision,
        event: WatcherEvent
    ):
        """
        Send notification to configured targets.

        Notification content:
        - Watcher that triggered
        - Triage summary and signal level
        - Event details
        - Action buttons: "Create Thread" | "Dismiss" | "Add to Existing Thread"
        """
        ...
```

### 4.6 Auto-Deliberation Graduation

A watcher earns auto-deliberation rights through demonstrated quality:

```python
class AutoDeliberationPolicy:
    """
    Policy for enabling auto-deliberation on a watcher.

    Requirements:
    1. Watcher has triggered at least 20 events
    2. Human has reviewed triage decisions for those events
    3. >70% of "high signal" triage decisions led to threads that produced useful output
    4. Human explicitly enables auto-deliberation for this watcher

    Once enabled:
    - Only "high signal" triage decisions auto-create threads
    - Rate limited: max 5 auto-threads per hour per watcher
    - Cost budget: auto-threads share the subreddit's monthly budget
    - Every auto-thread tagged for human review after completion
    """

    def can_auto_deliberate(self, watcher: WatcherConfig) -> bool:
        ...

    def enable_auto_deliberation(self, watcher_id: UUID, approved_by: UUID):
        """Human explicitly enables auto-deliberation after reviewing track record."""
        ...
```

### 4.7 Database Additions (Phase 4)

```sql
-- Watchers
CREATE TABLE watchers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subreddit_id UUID REFERENCES subreddits(id) NOT NULL,
    watcher_type VARCHAR(50) NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    source_config JSONB NOT NULL,
    trigger_condition TEXT NOT NULL,
    filter_expression TEXT,
    auto_create_thread BOOLEAN DEFAULT FALSE,
    notification_targets UUID[] DEFAULT '{}',
    triage_prompt TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    last_polled TIMESTAMP,
    last_triggered TIMESTAMP,
    total_events INT DEFAULT 0,
    total_threads_created INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Watcher events (audit log)
CREATE TABLE watcher_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    watcher_id UUID REFERENCES watchers(id) NOT NULL,
    event_details JSONB NOT NULL,
    triage_decision JSONB,          -- TriageDecision
    triage_tokens_used INT DEFAULT 0,
    human_action VARCHAR(20),       -- create_thread, dismiss, add_to_existing, pending
    thread_id UUID REFERENCES threads(id),  -- If a thread was created
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_watcher_events_watcher ON watcher_events(watcher_id);

-- Notifications
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    target_user_id UUID NOT NULL,
    watcher_event_id UUID REFERENCES watcher_events(id),
    title VARCHAR(500) NOT NULL,
    summary TEXT NOT NULL,
    signal_level VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'unread',  -- unread, read, acted
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_notifications_user ON notifications(target_user_id, status);

-- Add trigger tracking to threads
ALTER TABLE threads
    ADD COLUMN triggered_by VARCHAR(50) DEFAULT 'human',
    ADD COLUMN watcher_event_id UUID REFERENCES watcher_events(id);
```

### 4.8 Phase 4 Validation Criteria

1. Literature watcher detects new PubMed papers matching a configured query
2. Triage agent produces useful summaries (>80% rated "helpful" by human reviewers)
3. Human can create a thread directly from a notification with one click
4. Scheduled watcher fires on time and produces a relevant event
5. Webhook endpoint correctly receives and processes external events
6. After 20+ events, auto-deliberation can be enabled for a validated watcher
7. Rate limiting prevents runaway auto-deliberation costs

---

## Phase 5: Cross-Subreddit References and Feedback Loops (Weeks 17-20)

### 5.1 Cross-Subreddit References

**Only build this after Phase 3 memory is working well.** Cross-references are a special case of memory — they're findings from one subreddit that are relevant to another.

```python
class CrossReferenceDetector:
    """
    After a deliberation completes, check if findings are relevant
    to other subreddits.

    Stricter than originally designed. Uses entity overlap, not just
    embedding similarity, to reduce noise.
    """

    async def check(
        self,
        synthesis: Synthesis,
        source_subreddit: SubredditConfig,
        all_subreddits: List[SubredditConfig]
    ) -> List[CrossReference]:
        """
        Detection criteria (ALL must be met):
        1. Embedding similarity > 0.75 between synthesis and target subreddit's purpose
        2. At least one shared entity: same gene/target, same compound class,
           same disease area, or same cited paper
        3. The finding is actionable in the target subreddit's context

        If all criteria met → create CrossReference with status=pending
        Human reviews before any action is taken.
        """
        ...


class CrossReference(BaseModel):
    id: UUID
    source_thread_id: UUID
    source_subreddit_id: UUID
    target_subreddit_id: UUID
    relevance_score: float
    shared_entities: List[str]    # What entities are shared (for explainability)
    summary: str                   # Why this is relevant (generated)
    status: str                    # pending, accepted, dismissed
    action_taken: Optional[str]    # new_thread, added_to_existing, noted
```

### 5.2 Deliberation Comparison (Diffing)

When the same or related topic has been deliberated multiple times, produce a comparison:

```python
class DeliberationDiffer:
    """
    Compare two deliberations on related topics.

    Produces:
    - What's new (evidence or conclusions not in the earlier deliberation)
    - What changed (conclusions that shifted)
    - What was resolved (previously contested points that reached consensus)
    - What remains unresolved
    """

    async def diff(
        self,
        earlier: Synthesis,
        later: Synthesis
    ) -> DeliberationDiff:
        ...


class DeliberationDiff(BaseModel):
    new_evidence: List[str]
    changed_conclusions: List[ConclusionChange]
    resolved_disagreements: List[str]
    persistent_uncertainties: List[str]
    overall_trajectory: str  # "Strengthened", "Weakened", "Shifted", "Stable"


class ConclusionChange(BaseModel):
    topic: str
    before: str
    after: str
    reason: str  # What evidence drove the change
```

### 5.3 Outcome Tracking and Agent Calibration

**This requires ground truth data.** Track whether deliberation recommendations were followed and what happened.

```python
class OutcomeTracker:
    """
    Link deliberation recommendations to real-world outcomes.

    This is a manual process — humans report outcomes when they have them.
    The system uses outcomes to:
    1. Calibrate agent confidence (are high-confidence assessments more accurate?)
    2. Track agent prediction accuracy by domain
    3. Identify systematically overconfident or underconfident agents
    """

    @router.post("/api/threads/{thread_id}/outcome")
    async def report_outcome(self, thread_id: UUID, outcome: OutcomeReport):
        """Human reports what actually happened after following (or not) the deliberation's recommendations."""
        ...


class OutcomeReport(BaseModel):
    thread_id: UUID
    reported_by: UUID

    # What happened
    outcome_summary: str
    recommendations_followed: List[str]  # Which recommendations were acted on
    recommendations_ignored: List[str]   # Which were not
    outcome_aligned_with_assessment: bool  # Did reality match the assessment?

    # Specifics
    predictions_validated: List[str]    # Specific predictions that came true
    predictions_invalidated: List[str]  # Specific predictions that were wrong
    surprises: List[str]                # Things nobody predicted

    reported_at: datetime


class AgentCalibration:
    """
    Compute agent prediction accuracy over time.

    Only meaningful after 10+ outcomes have been reported.
    """

    async def compute_calibration(
        self, agent_id: UUID
    ) -> CalibrationReport:
        """
        For each deliberation this agent participated in:
        - What did the agent predict/assess?
        - What actually happened?
        - Was the agent's confidence level appropriate?

        Produce:
        - Overall accuracy rate
        - Calibration curve (confidence vs actual accuracy)
        - Domain-specific accuracy (is agent better in oncology than in neuro?)
        - Systematic biases (always overestimates efficacy? always underestimates toxicity?)
        """
        ...
```

### 5.4 Export and Integration

```python
# Synthesis export
@router.get("/api/threads/{thread_id}/export/{format}")
async def export_synthesis(thread_id: UUID, format: str):
    """
    Export synthesis in various formats.
    - markdown: Raw markdown
    - pdf: Formatted PDF with citations
    - json: Structured JSON for pipeline integration
    """
    ...

# Bulk API for external systems
@router.post("/api/external/submit")
async def external_submit(request: ExternalSubmitRequest):
    """
    External systems can submit hypotheses programmatically.
    Returns thread_id for polling results.
    """
    ...

@router.get("/api/external/results/{thread_id}")
async def external_results(thread_id: UUID):
    """
    Retrieve results for an externally-submitted thread.
    Returns synthesis in structured JSON format.
    """
    ...
```

### 5.5 Database Additions (Phase 5)

```sql
-- Cross-references
CREATE TABLE cross_references (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_thread_id UUID REFERENCES threads(id) NOT NULL,
    source_subreddit_id UUID REFERENCES subreddits(id) NOT NULL,
    target_subreddit_id UUID REFERENCES subreddits(id) NOT NULL,
    relevance_score FLOAT NOT NULL,
    shared_entities TEXT[] DEFAULT '{}',
    summary TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    action_taken VARCHAR(20),
    reviewed_by UUID,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Outcome reports
CREATE TABLE outcome_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID REFERENCES threads(id) NOT NULL,
    reported_by UUID NOT NULL,
    outcome_summary TEXT NOT NULL,
    recommendations_followed JSONB DEFAULT '[]',
    recommendations_ignored JSONB DEFAULT '[]',
    outcome_aligned BOOLEAN,
    predictions_validated JSONB DEFAULT '[]',
    predictions_invalidated JSONB DEFAULT '[]',
    surprises JSONB DEFAULT '[]',
    reported_at TIMESTAMP DEFAULT NOW()
);

-- Agent calibration snapshots (computed periodically)
CREATE TABLE agent_calibration (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id) NOT NULL,
    total_outcomes_evaluated INT NOT NULL,
    overall_accuracy FLOAT,
    calibration_data JSONB,      -- confidence_bucket → actual_accuracy mapping
    domain_accuracy JSONB,       -- domain → accuracy mapping
    systematic_biases JSONB,     -- Identified biases
    computed_at TIMESTAMP DEFAULT NOW()
);
```

### 5.6 Phase 5 Validation Criteria

1. Cross-references detected between related deliberations in different subreddits (precision >70% as evaluated by human)
2. Deliberation diff correctly identifies what changed between two related syntheses
3. Outcome tracking records at least 10 outcomes and produces a calibration report
4. Calibration data surfaces at least one agent-specific insight (e.g., "Chemistry agent overestimates synthetic feasibility")
5. Export produces usable PDF and JSON outputs
6. External API allows programmatic submission and result retrieval

---

## Open Research Questions (Beyond Phase 5)

These require significant R&D and are not specified as implementation tasks:

### 1. Agent Persona Evolution
Should agent personas update based on accumulated experience? A Chemistry agent that has participated in 100 deliberations has effectively "learned" — should its persona prompt evolve to reflect this? Risk: persona drift could degrade agent diversity. Potential approach: fork personas (v1, v2) and A/B test.

### 2. Optimal Panel Composition
Given a hypothesis, what's the optimal set of agents? This is a combinatorial optimization problem. With 12 base agents and subreddits needing 4-8, there are many possible panels. Phase 2 uses simple expertise matching. A future version could optimize panel composition based on outcome tracking data.

### 3. Dynamic Agent Creation
Phase 1-2 uses curated personas. Eventually, the system should be able to create new specialist agents for novel domains (e.g., "quantum computing drug design expert" when the field emerges). This requires solving the quality problem: how do you ensure an auto-generated persona produces genuinely different reasoning, not just different keywords?

### 4. Multi-Modal Evidence
Current tools return text (papers, database records). Future tools could handle images (microscopy, structural biology), time-series data (PK curves, gene expression), and molecular structures. This requires new tool adapters and potentially multi-modal LLM capabilities in the agent layer.

### 5. Adversarial Robustness
What happens when the system consistently reinforces a wrong conclusion? Even with red team agents, there's a risk of "groupthink" if all agents are trained on the same literature and reasoning patterns. This may require periodically injecting external perspectives or "resetting" agent priors.

---

*Phase 3-5 Implementation Prompt v2.0*
*Depends on: Phase 1-2 completion + 20 real deliberations*
*Created: 2026-02-11*
