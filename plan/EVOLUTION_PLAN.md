# Colloquip Evolution Plan: From Deliberation Engine to Social Platform

## Philosophy

We have a solid foundation — a working emergent deliberation engine with phase detection, energy-based termination, trigger-based self-selection, 6 agents, streaming API, and 181 passing tests. The new implementation specs (Phase 1-2 and Phase 3-5 docs) describe a more ambitious vision. This plan **evolves** the existing codebase toward that vision incrementally, rather than rewriting from scratch.

**Guiding principles:**
- Keep what works. The engine core (observer, energy, triggers) is proven — extend, don't replace.
- Stay on SQLite + SQLAlchemy for now. PostgreSQL migration is a Phase 3+ concern (when we need pgvector for embeddings).
- Keep the `src/colloquip/` package structure. Add new modules alongside existing ones.
- Every step must leave tests passing. No big-bang rewrites.
- Build with Phase 3+ in mind — design interfaces that the memory system, watchers, and cross-references can plug into later.

---

## What We're Adding (Priority Order)

### From Phase 1-2 Spec (Build Now)
1. **Subreddit system** — communities with purpose, output templates, participation models
2. **Agent pool & registry** — persistent agents, YAML personas, expertise-based recruitment
3. **10 curated personas** — 8 from spec + protein engineering + synthetic biology
4. **Tool system** — PubMed search, company docs, web search via LLM tool-use
5. **Output templates** — Assessment, Review, Analysis, Ideation (4 thinking types)
6. **Cost tracking** — per-thread token/cost tracking with budget kill switch
7. **Citation verification** — automated PubMed PMID validation
8. **Human participation** — Observer/Guided/Participant/Approver models
9. **Synthesis generator** — template-driven structured output with audit chains
10. **Mandatory red team** — topic-specific, always included

### Designed Now, Built Later (Phase 3+ Awareness)
- Memory system hooks (interfaces in place, implementation deferred)
- Watcher/triage system (data model awareness, no implementation)
- Cross-subreddit references (entity model supports it)
- Agent calibration (outcome tracking schema reserved)

---

## Step 1: Data Models (models.py)

Extend the existing Pydantic models. No breaking changes — all new fields are optional or additive.

### New Enums
```python
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
```

### New Models

**SubredditConfig** — community definition:
- id, name (slug), display_name, description
- purpose: SubredditPurpose (thinking_type, core_questions, decision_context, primary_domain, required_expertise)
- agent_roster: List[SubredditMembership]
- tool_configs: List[ToolConfig]
- output_template: OutputTemplate
- participation_model: ParticipationModel
- engine_overrides: Optional[EngineConfig] (reuse existing EngineConfig)
- max_cost_per_thread_usd, monthly_budget_usd
- always_include_red_team: bool = True
- created_by, timestamps

**BaseAgentIdentity** — persistent agent in the pool (replaces ephemeral AgentConfig):
- id, agent_type, display_name, expertise_tags
- persona_prompt, phase_mandates, domain_keywords, evaluation_criteria
- knowledge_scope: List[str]
- is_red_team, status: AgentStatus
- version: int (for persona updates)
- Loaded from YAML persona files

**SubredditMembership** — agent's scoped identity in a subreddit:
- id, agent_id, subreddit_id
- role: SubredditRole
- role_prompt: str (subreddit-specific focus)
- tool_access: List[str]
- threads_participated, total_posts
- joined_at

**OutputTemplate** — structured synthesis format:
- template_type: str
- sections: List[OutputSection] (name, description, required)
- metadata_fields: List[str]
- 4 default templates: ASSESSMENT, REVIEW, ANALYSIS, IDEATION

**Thread** — replaces/extends DeliberationSession for subreddit context:
- Extends existing session fields
- subreddit_id, created_by
- status: ThreadStatus
- synthesis: Optional[Synthesis]
- estimated_cost_usd

**Synthesis** — structured output from deliberation:
- id, thread_id, template_type
- sections: Dict[str, str]
- metadata: Dict[str, Any]
- audit_chains: List[AuditChain]
- citation_verification: CitationVerification

**AuditChain** — traceability for claims:
- claim, supporting_post_ids, citations, evidence_type, dissenting_agents

**CitationVerification** — automated check results:
- total_citations, verified, unverified, flagged, details

**CostRecord / CostSummary / ModelPricing** — cost tracking models

**ToolConfig** — tool available in a subreddit:
- tool_id, display_name, description, tool_type, connection_config, enabled

### Modified Models

**Post** — add fields:
- is_human: bool = False
- human_id: Optional[UUID]
- human_post_type: Optional[HumanPostType]
- tool_calls: List[dict] = []
- relevance_score: Optional[float]

**Citation** — enhance existing:
- source_type: str (pubmed, internal, web)
- source_id: str (PMID, record ID, URL)
- title, authors, year, journal, snippet
- url: Optional[str]
- retrieved_at: datetime

**DeliberationSession** — add:
- subreddit_id: Optional[UUID] (backward compatible)

**AgentDependencies** — add:
- membership: Optional[SubredditMembership]
- available_tools: List[dict] = []
- subreddit: Optional[SubredditConfig]

---

## Step 2: Agent Personas (YAML Library)

Create `src/colloquip/agents/personas/` with 10 curated YAML files. Each persona follows the depth shown in the Phase 1-2 spec: specific background, weighted evaluation criteria, reasoning style, known blind spots, interaction style, and phase mandates.

### Persona Roster (10 agents)

| # | File | Agent Type | Key Perspective |
|---|------|-----------|----------------|
| 1 | `molecular_biology.yaml` | molecular_biology | Mechanistic rigor, genetic evidence, pathway biology |
| 2 | `medicinal_chemistry.yaml` | medicinal_chemistry | Druggability, SAR, synthetic feasibility |
| 3 | `admet.yaml` | admet | Drug-like properties, PK/PD, safety margins |
| 4 | `clinical.yaml` | clinical | Clinical translatability, trial design, patient selection |
| 5 | `regulatory.yaml` | regulatory | Regulatory pathway, precedent, risk classification |
| 6 | `computational_biology.yaml` | computational_biology | Data analysis, modeling, statistical rigor |
| 7 | `protein_engineering.yaml` | protein_engineering | Protein design, directed evolution, stability/activity tradeoffs |
| 8 | `synthetic_biology.yaml` | synthetic_biology | Genetic circuits, pathway engineering, chassis organism selection |
| 9 | `red_team_general.yaml` | red_team_general | Adversarial: hidden assumptions, failure modes, premature consensus |
| 10 | `red_team_biology.yaml` | red_team_biology | Domain-specific: biological pitfalls, translational failures |

**Persona YAML schema:**
```yaml
agent_type: str
display_name: str
expertise_tags: [str]
knowledge_scope: [str]
persona_prompt: |
  Multi-paragraph persona with:
  - Background (specific institutions, years of experience)
  - Evaluation priorities (weighted, sum to 1.0)
  - Reasoning style (how they approach problems)
  - Known blind spots (specific, not generic)
  - Interaction style (how they engage with other agents)
evaluation_criteria:
  criterion_name: weight  # Sum to 1.0
phase_mandates:
  explore: |
    Phase-specific behavior instructions
  debate: |
    ...
  deepen: |
    ...
  converge: |
    ...
domain_keywords: [str]
is_red_team: bool
```

**Persona loader** (`agents/persona_loader.py`):
- Load all YAML files from personas/ directory
- Validate against schema
- Convert to BaseAgentIdentity models
- Cache for reuse

---

## Step 3: Agent Pool & Registry (registry.py)

### AgentRegistry

```python
class AgentRegistry:
    """Global agent pool. Agents are reused across subreddits."""

    def __init__(self, repo: SessionRepository):
        self.repo = repo
        self._pool: Dict[UUID, BaseAgentIdentity] = {}

    async def load_pool(self) -> None:
        """Load all agents from DB + persona YAML files."""

    async def find_agent(self, expertise: str, domain: str) -> Optional[BaseAgentIdentity]:
        """Find best matching agent in pool by expertise + domain."""

    async def find_or_create(self, config: dict) -> BaseAgentIdentity:
        """Find matching agent or create from curated persona library."""

    async def recruit_for_subreddit(
        self, purpose: SubredditPurpose, subreddit_id: UUID
    ) -> RecruitmentResult:
        """
        Match required expertise to agents in pool.
        Returns: memberships (assigned) + gaps (missing expertise).
        Always ensures at least one red team agent.
        """

    async def ensure_red_team(
        self, subreddit: SubredditConfig, memberships: List[SubredditMembership]
    ) -> Optional[SubredditMembership]:
        """Add topic-specific red team if none assigned."""
```

### Recruitment Scoring

```python
def _score_candidate(agent: BaseAgentIdentity, expertise: str, domain: str) -> float:
    """
    Score agent against required expertise:
    - Exact expertise_tag match: +0.5
    - Partial tag overlap (token match): +0.2 per token
    - Domain keyword match: +0.3
    - Knowledge scope overlap: +0.2
    """
```

### RecruitmentResult

```python
class RecruitmentResult(BaseModel):
    memberships: List[SubredditMembership]
    gaps: List[ExpertiseGap]

class ExpertiseGap(BaseModel):
    expertise: str
    domain: str
    is_red_team: bool = False
    has_curated_template: bool  # Is there a YAML persona for this?
```

---

## Step 4: Tool System (tools/)

### 4.1 Tool Interface (`tools/interface.py`)

```python
class AgentTool(Protocol):
    name: str
    description: str
    tool_schema: dict  # Claude tool-use schema

    async def execute(self, **kwargs) -> ToolResult

class ToolResult(BaseModel):
    source: str
    query: str
    results: List[SearchResult]
    truncated: bool = False

class SearchResult(BaseModel):
    title: str
    authors: List[str] = []
    abstract: str = ""
    url: str = ""
    doi: str = ""
    year: Optional[int] = None
    source_id: str = ""  # PMID, internal ID, etc.
```

### 4.2 PubMed Tool (`tools/pubmed.py`)

- NCBI E-utilities API: esearch → efetch pipeline
- Methods: search(query, max_results, date_from), get_abstract(pmid), find_related(pmids)
- Returns structured Citation objects with [PUBMED:PMID] references
- Rate-limited (3 req/sec without API key)
- MockPubMedTool for testing

### 4.3 Company Docs Tool (`tools/company_docs.py`)

- Local directory search (markdown/text files)
- Simple keyword matching with TF-IDF scoring
- Returns [INTERNAL:record-id] references
- Extensible interface for Elasticsearch, vector DB, etc.
- MockCompanyDocsTool for testing

### 4.4 Web Search Tool (`tools/web_search.py`)

- Semantic Scholar API (free, structured academic results)
- Fallback: configurable provider
- Returns [WEB:url] references
- MockWebSearchTool for testing

### 4.5 Citation Verifier (`tools/citation_verifier.py`)

- Validates [PUBMED:PMID] citations against NCBI API
- Batch verification after synthesis generation
- Returns CitationVerification with verified/unverified/flagged counts
- MockCitationVerifier for testing

### 4.6 Tool Registry (`tools/registry.py`)

```python
class ToolRegistry:
    """Maps tool IDs to implementations. Configures per subreddit."""

    _tools: Dict[str, Type[AgentTool]]  # "pubmed" → PubMedTool class
    _mock_tools: Dict[str, Type[AgentTool]]  # "pubmed" → MockPubMedTool class

    def get_tools_for_subreddit(self, subreddit: SubredditConfig) -> List[AgentTool]:
        """Instantiate tools based on subreddit's tool_configs."""

    def get_claude_tool_schemas(self, tools: List[AgentTool]) -> List[dict]:
        """Convert tools to Claude API tool-use format."""
```

### 4.7 LLM Tool-Use Integration

Extend LLMInterface and AnthropicLLM:

```python
# LLMInterface.generate() — add optional tools parameter
async def generate(
    self, system_prompt: str, user_prompt: str,
    tools: Optional[List[dict]] = None,
    tool_executor: Optional[Callable] = None,
) -> LLMResult

# AnthropicLLM — implement tool-use loop:
# 1. Send message with tools
# 2. If response contains tool_use blocks → execute tools → send results back
# 3. Continue until LLM produces final text response
# 4. Parse into LLMResult with citations from tool results

# MockLLM — occasionally simulate tool calls when tools provided
```

---

## Step 5: Output Templates & Synthesis

### 5.1 Templates (models or config)

Define 4 default output templates directly in the models (as shown in Phase 1-2 spec):
- ASSESSMENT_TEMPLATE: Executive Summary, Evidence For, Evidence Against, Key Risks, Minority Positions, Recommended Next Steps, Decision Framework
- REVIEW_TEMPLATE: Publication Summary, Internal Data Comparison, Agreements, Contradictions, Gaps Identified, Action Items
- ANALYSIS_TEMPLATE: Data Summary, Key Findings, Immediate Actions, Aspirational Actions, Resource Requirements, External Context
- IDEATION_TEMPLATE: Opportunity Landscape, Top Ideas, Novel Connections, Quick Wins, Moonshots, Next Steps

### 5.2 Synthesis Generator (`engine/synthesis.py`)

Replace the current consensus map generation with a proper synthesis generator:

```python
class SynthesisGenerator:
    async def generate(
        self, thread: Thread, posts: List[Post], template: OutputTemplate
    ) -> Synthesis:
        """
        1. Build synthesis prompt with all posts + template instructions
        2. LLM generates structured sections
        3. Parse into Synthesis model
        4. Extract audit chains (claim → post → citation)
        5. Run citation verification
        """
```

The existing `ConsensusMap` extraction logic (agreements, disagreements, minority positions, connections) remains useful as input to the synthesis prompt — we reference it, not replace it.

### 5.3 Audit Chain Extraction

```python
class AuditChainExtractor:
    def extract(self, synthesis_text: str, posts: List[Post]) -> List[AuditChain]:
        """Link claims in synthesis back to supporting posts and their citations."""
```

---

## Step 6: Cost Tracking (`engine/cost_tracker.py`)

```python
class CostTracker:
    def __init__(self, pricing: ModelPricing): ...
    def record(self, thread_id: UUID, input_tokens: int, output_tokens: int, model: str): ...
    def total_tokens(self, thread_id: UUID) -> int: ...
    def estimated_cost(self, thread_id: UUID) -> float: ...
    def thread_summary(self, thread_id: UUID) -> CostSummary: ...
    def check_budget(self, thread_id: UUID, max_usd: float) -> bool: ...
```

Integrated into the engine loop: after each LLM call, record tokens. If budget exceeded, terminate with FAILED status but still generate synthesis from available posts.

---

## Step 7: Human Participation

### 7.1 Participation Model Enforcement

```python
async def validate_human_participation(
    subreddit: SubredditConfig, post_type: HumanPostType
) -> bool:
    """
    OBSERVER: no posts allowed
    GUIDED: QUESTION and REDIRECT only
    PARTICIPANT: all types
    APPROVER: all types + deliberation pauses at phase transitions
    """
```

### 7.2 Human Post Handling in Engine

Extend the existing `handle_intervention()` to support typed human posts:
- QUESTION → energy boost + all relevant agents respond
- DATA → energy boost (NEW_KNOWLEDGE) + agents incorporate
- REDIRECT → can influence phase transition
- COMMENT → treated as normal post

### 7.3 Approver Model

When participation_model == APPROVER:
- Engine pauses at each phase transition
- Yields a `PauseEvent` with phase info
- Resumes when human approves via API

---

## Step 8: Prompt Builder Evolution (`agents/prompts.py`)

Add a new prompt version (v3) that incorporates:

1. **Base persona** (from YAML)
2. **Subreddit role** (from membership.role_prompt)
3. **Subreddit context** (purpose, core questions, decision context)
4. **Phase mandate** (from persona)
5. **Tool instructions** (available tools + citation requirements)
6. **Thread context** (hypothesis + conversation history)
7. **Response guidelines** (formatting, citation format, quality bar)

This replaces the current v1/v2 system prompt builders. The existing `build_system_prompt` and `build_user_prompt` functions remain for backward compatibility.

### Citation Requirements (injected into every prompt)
```
- EVERY factual claim MUST cite a source
- Format: [PUBMED:PMID] for literature, [INTERNAL:record-id] for internal data
- If you cannot find evidence, say so explicitly
- Distinguish: DIRECT EVIDENCE vs INFERENCE vs OPINION
- Never fabricate citations. Ever.
```

---

## Step 9: Engine Evolution (`engine.py`)

### Extend EmergentDeliberationEngine

The core loop stays the same. We add:

1. **Subreddit awareness**: engine receives subreddit config, uses its output template and tool config
2. **Tool access**: pass tools to agents during post generation
3. **Cost tracking**: record tokens after each LLM call, check budget
4. **Synthesis generation**: use template-driven SynthesisGenerator instead of basic ConsensusMap
5. **Citation verification**: post-synthesis automated check
6. **Human participation**: respect participation model, support pause/resume
7. **Typed events**: yield Synthesis, CostUpdate, PauseEvent alongside existing Post/PhaseSignal/EnergyUpdate

```python
class EmergentDeliberationEngine:
    def __init__(
        self,
        agents, observer, energy_calculator, trigger_evaluator,
        config,
        synthesis_generator: Optional[SynthesisGenerator] = None,  # NEW
        cost_tracker: Optional[CostTracker] = None,                # NEW
        tool_registry: Optional[ToolRegistry] = None,              # NEW
    ): ...

    async def run_deliberation(
        self,
        session: DeliberationSession,
        hypothesis: str,
        subreddit: Optional[SubredditConfig] = None,  # NEW, optional for backward compat
    ) -> AsyncIterator[...]:
        # Existing loop + new features
```

**Backward compatibility**: when subreddit is None, engine behaves exactly as before (no tools, no cost tracking, basic consensus map synthesis). All 181 existing tests continue passing.

---

## Step 10: Database Schema Evolution (`db/tables.py`)

### New Tables

```python
class DBSubreddit(Base):
    __tablename__ = "subreddits"
    id, name (unique), display_name, description,
    purpose (JSON), output_template (JSON), participation_model,
    engine_overrides (JSON), tool_configs (JSON),
    max_cost_per_thread_usd, monthly_budget_usd,
    always_include_red_team, created_by, created_at, updated_at

class DBAgentIdentity(Base):
    __tablename__ = "agent_identities"
    id, agent_type, display_name, expertise_tags (JSON),
    persona_prompt, phase_mandates (JSON), domain_keywords (JSON),
    knowledge_scope (JSON), evaluation_criteria (JSON),
    is_red_team, status, version, created_at

class DBSubredditMembership(Base):
    __tablename__ = "subreddit_memberships"
    id, agent_id (FK), subreddit_id (FK), role, role_prompt,
    tool_access (JSON), threads_participated, total_posts, joined_at
    UniqueConstraint(agent_id, subreddit_id)

class DBSynthesis(Base):
    __tablename__ = "syntheses"
    id, thread_id (FK, unique), template_type,
    sections (JSON), metadata (JSON), audit_chains (JSON),
    total_citations, citation_verification (JSON),
    tokens_used, created_at

class DBCostRecord(Base):
    __tablename__ = "cost_records"
    id, thread_id (FK), input_tokens, output_tokens,
    model, estimated_cost_usd, recorded_at

class DBToolConfig(Base):
    __tablename__ = "tool_configs"
    id, subreddit_id (FK), tool_id, display_name,
    description, tool_type, connection_config (JSON), enabled
    UniqueConstraint(subreddit_id, tool_id)
```

### Modified Tables

```python
# DBSession — add:
subreddit_id = Column(String, ForeignKey("subreddits.id"), nullable=True)
created_by = Column(String, nullable=True)
estimated_cost_usd = Column(Float, default=0.0)

# DBPost — add:
is_human = Column(Boolean, default=False)
human_id = Column(String, nullable=True)
human_post_type = Column(String, nullable=True)
tool_calls = Column(JSON, default=[])
relevance_score = Column(Float, nullable=True)
```

### Repository Extensions

Add to SessionRepository:
- Subreddit CRUD: save_subreddit, get_subreddit, get_subreddit_by_name, list_subreddits
- Agent CRUD: save_agent, get_agent, list_agents, find_agents_by_expertise
- Membership CRUD: add_membership, remove_membership, get_subreddit_members, get_agent_subreddits
- Synthesis CRUD: save_synthesis, get_synthesis
- Cost CRUD: save_cost_record, get_thread_costs, get_subreddit_costs
- Tool CRUD: save_tool_config, get_subreddit_tools

---

## Step 11: API Routes Evolution (`api/routes.py`)

### New Endpoints

**Subreddits:**
- `POST /api/subreddits` — Create subreddit (runs recruitment, returns config with gaps)
- `GET /api/subreddits` — List all subreddits
- `GET /api/subreddits/{name}` — Subreddit details with roster
- `PUT /api/subreddits/{id}/roster` — Add/remove agents
- `POST /api/subreddits/{id}/activate` — Activate after human review
- `GET /api/subreddits/{name}/threads` — List threads in subreddit
- `POST /api/subreddits/{name}/threads` — Create thread (deliberation) in subreddit

**Agents:**
- `GET /api/agents` — List agent pool (filterable by expertise)
- `GET /api/agents/{id}` — Agent details + subreddit memberships

**Costs:**
- `GET /api/costs/summary` — Platform-wide cost summary
- `GET /api/threads/{id}/costs` — Thread cost breakdown

**Human Participation:**
- `POST /api/threads/{id}/posts` — Human post (validates against participation model)
- `POST /api/threads/{id}/approve-phase` — Approve phase transition (approver model)

### Modified Endpoints

- `POST /api/deliberations` — add optional subreddit_id; when present, loads subreddit config, recruits agents, configures tools
- SSE stream — add new event types: `synthesis`, `cost_update`, `citation_verification`, `pause`

### Backward Compatibility

All existing endpoints continue to work unchanged. The `/api/deliberations` endpoint without subreddit_id behaves exactly as before.

---

## Step 12: Configuration Updates

### `config/platform.yaml` (new)

```yaml
platform:
  name: "Colloquip Deliberation Platform"
  llm_model: "claude-sonnet-4-5-20250929"
  synthesis_model: "claude-sonnet-4-5-20250929"

subreddit_defaults:
  min_agents: 3
  max_agents: 8
  always_include_red_team: true
  participation_model: "guided"
  max_cost_per_thread_usd: 5.0

cost:
  model_pricing:
    model_name: "claude-sonnet-4-5-20250929"
    cost_per_input_token: 0.000003
    cost_per_output_token: 0.000015
  alert_threshold_usd: 3.0
```

### Default Subreddit Configs (`config/subreddits/`)

YAML files for default subreddits:
- `target_validation.yaml` — Assessment type, drug discovery agents
- `literature_review.yaml` — Review type, subset of agents + computational biology
- `novel_ideas.yaml` — Ideation type, broader agent set

---

## Implementation Order

### Sprint 1: Foundation (Models + Personas + DB)

```
1.1  New enums and models in models.py
1.2  Write 10 persona YAML files
1.3  Persona loader (agents/persona_loader.py)
1.4  New database tables (db/tables.py)
1.5  Repository extensions (db/repository.py)
1.6  Unit tests for models, persona loading, repository CRUD
```

**Gate**: All existing 181 tests pass + new model/DB tests pass.

### Sprint 2: Agent Pool + Registry + Recruitment

```
2.1  AgentRegistry class (registry.py)
2.2  Recruitment scoring logic
2.3  Red team enforcement (ensure_red_team)
2.4  Unit tests for registry, recruitment, gap detection
```

**Gate**: Can create subreddit → recruit agents from pool → report gaps → red team guaranteed.

### Sprint 3: Tool System

```
3.1  Tool interface (tools/interface.py)
3.2  PubMed tool + mock (tools/pubmed.py)
3.3  Company docs tool + mock (tools/company_docs.py)
3.4  Web search tool + mock (tools/web_search.py)
3.5  Citation verifier + mock (tools/citation_verifier.py)
3.6  Tool registry (tools/registry.py)
3.7  LLM tool-use integration (extend llm/interface.py, llm/anthropic.py, llm/mock.py)
3.8  Unit tests for each tool, registry, LLM tool-use
```

**Gate**: Mock agents can "call" tools and produce posts with real citation format.

### Sprint 4: Output Templates + Synthesis + Cost Tracking

```
4.1  Output templates (4 default templates)
4.2  Synthesis generator (engine/synthesis.py)
4.3  Audit chain extraction
4.4  Cost tracker (engine/cost_tracker.py)
4.5  Integration into engine (extend engine.py)
4.6  Unit tests for synthesis, cost tracking, audit chains
```

**Gate**: Engine produces template-driven synthesis with cost tracking.

### Sprint 5: Prompt Builder v3 + Human Participation

```
5.1  Prompt builder v3 (agents/prompts.py) — full layered prompt
5.2  Human participation model enforcement
5.3  Human post handling in engine
5.4  Approver model (pause/resume)
5.5  Tests for prompts, participation, human posts
```

**Gate**: Agents receive full layered prompts with tool instructions and citation requirements. Human posts work with all participation models.

### Sprint 6: API + Integration

```
6.1  Subreddit API endpoints
6.2  Agent pool API endpoints
6.3  Cost API endpoints
6.4  Human participation API endpoints
6.5  Updated deliberation endpoint (subreddit-aware)
6.6  Updated SSE stream (new event types)
6.7  Default subreddit seeding (target_validation, literature_review, novel_ideas)
6.8  Full API test coverage
```

**Gate**: End-to-end: create subreddit → submit hypothesis → get template-driven synthesis with citations and cost.

### Sprint 7: Integration Testing + Polish

```
7.1  E2E test: target_validation subreddit with ASSESSMENT_TEMPLATE
7.2  E2E test: literature_review subreddit with REVIEW_TEMPLATE
7.3  E2E test: novel_ideas subreddit with IDEATION_TEMPLATE
7.4  E2E test: human question injection mid-deliberation
7.5  E2E test: cost budget kill switch
7.6  E2E test: citation verification catches fake PMIDs (mock)
7.7  Backward compatibility: all 181 original tests still pass
7.8  CLI updates (if needed for new subreddit commands)
```

**Gate**: Phase 1-2 validation criteria met (from spec doc).

---

## Phase 3+ Preparation (Design Now, Build Later)

### Memory System Hooks

In Sprint 4, the SynthesisGenerator returns a Synthesis object. We add a hook:

```python
# In engine.py, after synthesis generation:
if self.memory_hook:
    await self.memory_hook(synthesis, posts, subreddit)
```

This is a no-op in Phase 1-2. In Phase 3, it becomes the synthesis-level RAG storage (pgvector embedding + storage). The interface is ready.

### Agent Calibration Schema

In the DB schema, we reserve space for outcome tracking (Phase 5):

```python
# Not implemented, but the foreign key exists:
# DBSynthesis.thread_id → can be linked to outcome_reports later
```

### Watcher Awareness

The SubredditConfig model includes:
```python
# Reserved for Phase 4 — not populated in Phase 1-2
watchers: List[WatcherConfig] = []
```

---

## File Change Summary

| File | Action | Description |
|------|--------|-------------|
| `src/colloquip/models.py` | **Modify** | New enums, SubredditConfig, BaseAgentIdentity, SubredditMembership, OutputTemplate, Thread, Synthesis, AuditChain, CitationVerification, CostRecord, ToolConfig, HumanPostType. Extend Post, Citation, DeliberationSession, AgentDependencies |
| `src/colloquip/registry.py` | **New** | AgentRegistry, recruitment scoring, red team enforcement |
| `src/colloquip/agents/persona_loader.py` | **New** | YAML persona loading + validation |
| `src/colloquip/agents/personas/*.yaml` | **New** | 10 curated persona files |
| `src/colloquip/agents/prompts.py` | **Modify** | Add v3 prompt builder with layered assembly |
| `src/colloquip/agents/base.py` | **Modify** | Support tool-use loop, membership-aware post generation |
| `src/colloquip/tools/__init__.py` | **New** | Package init |
| `src/colloquip/tools/interface.py` | **New** | AgentTool protocol, ToolResult, SearchResult |
| `src/colloquip/tools/pubmed.py` | **New** | PubMed E-utilities + mock |
| `src/colloquip/tools/company_docs.py` | **New** | Local doc search + mock |
| `src/colloquip/tools/web_search.py` | **New** | Semantic Scholar + mock |
| `src/colloquip/tools/citation_verifier.py` | **New** | PMID validation + mock |
| `src/colloquip/tools/registry.py` | **New** | Tool registry per subreddit |
| `src/colloquip/engine.py` | **Modify** | Add subreddit awareness, tool passing, cost tracking, synthesis generation, human participation |
| `src/colloquip/engine/synthesis.py` | **New** | SynthesisGenerator, template-driven output |
| `src/colloquip/engine/cost_tracker.py` | **New** | CostTracker, ModelPricing |
| `src/colloquip/llm/interface.py` | **Modify** | Add tools parameter to generate() |
| `src/colloquip/llm/anthropic.py` | **Modify** | Tool-use loop implementation |
| `src/colloquip/llm/mock.py` | **Modify** | Simulate tool calls in mock mode |
| `src/colloquip/db/tables.py` | **Modify** | New tables: subreddits, agent_identities, subreddit_memberships, syntheses, cost_records, tool_configs. Extend sessions, posts |
| `src/colloquip/db/repository.py` | **Modify** | CRUD for all new entities |
| `src/colloquip/api/routes.py` | **Modify** | New subreddit, agent, cost, human participation endpoints. Updated deliberation endpoints |
| `src/colloquip/api/app.py` | **Modify** | SessionManager extended for subreddit-aware deliberations |
| `config/platform.yaml` | **New** | Platform-level configuration |
| `config/subreddits/*.yaml` | **New** | Default subreddit definitions |
| `tests/test_models.py` | **Modify** | Tests for new models |
| `tests/test_registry.py` | **New** | Agent pool, recruitment, red team tests |
| `tests/test_persona_loader.py` | **New** | YAML loading + validation tests |
| `tests/test_tools.py` | **New** | Tool interface, mock execution, PubMed parsing |
| `tests/test_synthesis.py` | **New** | Synthesis generation, audit chains, citation verification |
| `tests/test_cost.py` | **New** | Cost tracking, budget enforcement |
| `tests/test_participation.py` | **New** | Human participation model tests |
| `tests/test_social.py` | **New** | Subreddit creation, membership, cross-subreddit agents |
| `tests/test_api.py` | **Modify** | New endpoint tests |
| `tests/test_db.py` | **Modify** | Repository tests for new tables |

---

## Validation Criteria (Phase 1-2 Complete)

From the spec doc, adapted for our evolved codebase:

| # | Criterion | How to Verify |
|---|----------|---------------|
| 1 | Submit hypothesis to r/target_validation → get synthesis | E2E test |
| 2 | Synthesis follows ASSESSMENT_TEMPLATE (all 7 sections) | Automated: section names |
| 3 | >80% of citations are real PubMed papers | Automated: citation verifier (mock in tests) |
| 4 | Cost tracking shows tokens + estimated USD | Automated: cost summary |
| 5 | Red team agent raises substantive concerns | Manual review / test assertion |
| 6 | Different subreddits → different output templates | Automated: template section validation |
| 7 | Agent recruitment reports gaps for missing expertise | Unit test |
| 8 | Human can inject question mid-deliberation | Integration test |
| 9 | Each agent has recognizable voice | Blind test (manual) |
| 10 | All 181 original tests still pass | CI |
| 11 | Protein engineering + synthetic biology agents participate in relevant subreddits | Integration test |

---

## What We Explicitly Defer

| Feature | Deferred To | Reason |
|---------|------------|--------|
| Memory system (synthesis RAG, typed memories) | Phase 3 | Needs real usage data to calibrate |
| PostgreSQL migration | Phase 3 | Needed for pgvector; SQLite fine for now |
| Event-driven watchers + triage | Phase 4 | Needs 20+ real deliberations first |
| Cross-subreddit references | Phase 5 | Needs memory system working first |
| Agent calibration + outcome tracking | Phase 5 | Needs ground truth data |
| LLM-generated agent personas | Never (Phase 1-2) | Curated only; quality control |
| React dashboard updates | Separate PR | UI follows API, not vice versa |
