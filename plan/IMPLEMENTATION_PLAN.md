# Colloquip: Implementation Plan

## Guiding Principles

1. **Make it work** → **Make it right** → **Make it fast**
2. Every component testable in isolation with no LLM calls required
3. Interfaces first, implementations second — enables pivoting
4. Configuration-driven behavior — change tuning without code changes
5. Minimal dependencies — add only what's needed at each phase

---

## Target Architecture

```
colloquip/
├── src/
│   └── colloquip/
│       ├── __init__.py
│       ├── models.py          # Pydantic data models (Phase, Post, etc.)
│       ├── config.py          # Configuration loading & defaults
│       ├── energy.py          # Energy calculator + termination logic
│       ├── observer.py        # Observer agent (rule-based phase detection)
│       ├── triggers.py        # Trigger evaluator (agent self-selection)
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── base.py        # BaseDeliberationAgent
│       │   └── prompts.py     # Prompt builder (persona + phase mandate)
│       ├── engine.py          # Main deliberation loop
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── interface.py   # LLM protocol/interface
│       │   └── mock.py        # Mock LLM for testing
│       └── api/
│           ├── __init__.py
│           ├── app.py         # FastAPI application
│           ├── routes.py      # REST endpoints
│           └── ws.py          # WebSocket endpoint
├── tests/
│   ├── __init__.py
│   ├── conftest.py            # Shared fixtures (posts, agents, sessions)
│   ├── test_models.py
│   ├── test_energy.py
│   ├── test_observer.py
│   ├── test_triggers.py
│   ├── test_agents.py
│   ├── test_engine.py
│   └── test_api.py
├── config/
│   ├── agents.yaml            # Agent personas, keywords, knowledge scopes
│   └── engine.yaml            # Engine, observer, energy, trigger settings
├── docs/                      # Design specification documents
│   ├── README.md
│   ├── SYSTEM_DESIGN.md
│   ├── ENERGY_MODEL.md
│   ├── OBSERVER_SPEC.md
│   ├── AGENT_PROMPTS.md
│   └── TRIGGER_RULES.md
├── plan/                      # This plan
│   └── IMPLEMENTATION_PLAN.md
├── pyproject.toml
└── README.md
```

---

## Phase 1: Core Domain Models & Pure Logic (Make It Work)

**Goal**: All core business logic works, fully tested, zero external dependencies.

### Step 1.1 — Project Scaffolding

- [ ] `pyproject.toml` with Python 3.11+, pytest, pydantic
- [ ] Basic package structure (`src/colloquip/`)
- [ ] Test infrastructure (`tests/`, conftest with factories)
- [ ] Verify `pytest` runs green with a placeholder test

**Success criteria**: `pytest` passes, package importable.

### Step 1.2 — Data Models (`models.py`)

Implement all Pydantic models from SYSTEM_DESIGN.md:

- [ ] `Phase` enum (EXPLORE, DEBATE, DEEPEN, CONVERGE, SYNTHESIS)
- [ ] `AgentStance` enum (SUPPORTIVE, CRITICAL, NEUTRAL, NOVEL_CONNECTION)
- [ ] `Citation`, `Post`, `ConversationMetrics`, `PhaseSignal`
- [ ] `EnergyUpdate`, `DeliberationSession`, `ConsensusMap`
- [ ] `AgentConfig`, `EngineConfig`
- [ ] Test factory functions in `conftest.py` (`create_post()`, `create_session()`, etc.)

**Tests**:
- Model validation (required fields, enums, type coercion)
- Factory functions produce valid models
- Serialization/deserialization round-trip

**Success criteria**: All models instantiate, validate, and serialize correctly.

### Step 1.3 — Energy Calculator (`energy.py`)

Implement from ENERGY_MODEL.md:

- [ ] `calculate_energy(posts, window=10) -> float`
- [ ] `_calculate_novelty_component(recent) -> float`
- [ ] `_calculate_disagreement_component(recent) -> float`
- [ ] `_calculate_question_component(recent, all_posts) -> float`
- [ ] `_calculate_staleness_penalty(recent, all_posts) -> float`
- [ ] `should_terminate(posts, energy_history, config) -> (bool, str)`
- [ ] `inject_energy(source, current_energy) -> float`
- [ ] `EnergyCalculator` class wrapping the above with config

**Tests**:
- High novelty posts → high energy
- All supportive posts → low disagreement component
- Many unanswered questions → high question component
- Repeated content → high staleness penalty
- Energy below threshold for 3 rounds → termination
- Minimum post guard prevents early termination
- Energy injection boosts value correctly
- Energy always clamped to [0.0, 1.0]

**Success criteria**: Energy values match expected ranges from ENERGY_MODEL.md calibration section.

### Step 1.4 — Observer Agent (`observer.py`)

Implement from OBSERVER_SPEC.md:

- [ ] Metric functions: `question_rate()`, `disagreement_rate()`, `topic_diversity()`, `citation_density()`, `novelty_average()`, `posts_since_novel()`
- [ ] `ConversationMetrics` calculation from post list
- [ ] `detect_phase(metrics) -> Optional[Phase]` (rule-based)
- [ ] `ObserverAgent` class with hysteresis
- [ ] `calculate_confidence()` function
- [ ] `generate_observation(metrics) -> Optional[str]` (meta-observations)

**Tests**:
- High question rate + diverse agents → EXPLORE detected
- High disagreement + citations → DEBATE detected
- Low diversity + high novelty → DEEPEN detected
- Low energy + stagnation → CONVERGE detected
- Ambiguous metrics → no phase change (returns None)
- Hysteresis: single signal doesn't cause transition
- Hysteresis: 3 consecutive signals causes transition
- Hysteresis: interrupted signal resets counter
- Confidence high when stable, drops during pending transition
- Meta-observations fire only when thresholds met

**Success criteria**: Phase detection matches truth table from OBSERVER_SPEC.md. Hysteresis prevents oscillation in noisy scenarios.

### Step 1.5 — Trigger Evaluator (`triggers.py`)

Implement from TRIGGER_RULES.md:

- [ ] `check_relevance()` — domain keyword matching
- [ ] `check_disagreement()` — strong claims in domain
- [ ] `check_question()` — unanswered domain questions
- [ ] `check_silence_breaking()` — agent silent too long
- [ ] `check_bridge_opportunity()` — cross-agent connections
- [ ] `check_uncertainty_response()` — uncertainty in domain
- [ ] Red Team rules: `check_consensus_forming()`, `check_criticism_gap()`, `check_premature_convergence()`
- [ ] `TriggerEvaluator` class with phase modulation
- [ ] `apply_refractory_period()` function

**Tests**:
- Biology keywords in recent posts → Biology relevance fires
- Strong claim in chemistry domain → Chemistry disagreement fires
- Unanswered question about toxicity → ADMET question fires
- Agent silent for 7 posts → silence breaking fires
- Two agents discussing overlapping concepts → bridge fires
- Uncertainty in domain → uncertainty response fires
- 3+ supportive posts → Red Team consensus trigger fires
- No criticism in 3+ posts → Red Team criticism gap fires
- Phase modulation adjusts thresholds (EXPLORE vs DEEPEN)
- Refractory period blocks rapid re-posting

**Success criteria**: Each trigger fires correctly in isolation. Phase modulation shifts thresholds as specified.

### Step 1.6 — Configuration (`config.py`)

- [ ] `EngineConfig`, `ObserverConfig`, `EnergyConfig`, `TriggerConfig` dataclasses
- [ ] YAML loading from `config/` directory
- [ ] Defaults matching values in docs (max_turns=30, threshold=0.2, etc.)
- [ ] `config/engine.yaml` and `config/agents.yaml` with defaults from docs

**Tests**:
- Default config matches documented values
- YAML override correctly merges with defaults
- Invalid config raises clear validation errors

**Success criteria**: Config loads cleanly, defaults match documentation.

---

## Phase 2: Agent Framework & Deliberation Loop (Make It Right)

**Goal**: Full deliberation loop runs end-to-end with mock LLM.

### Step 2.1 — LLM Interface & Mock (`llm/`)

- [ ] `LLMInterface` protocol (abstract base)
- [ ] `MockLLM` implementation that returns deterministic, configurable responses
- [ ] Mock returns structured output matching `Post` fields (stance, claims, questions, novelty)
- [ ] Configurable mock behaviors (always supportive, always critical, mixed, etc.)

**Tests**:
- Mock returns valid structured output
- Mock behavior modes produce expected stances
- Interface contract enforced

**Success criteria**: Mock LLM enables full integration testing without API calls.

### Step 2.2 — Agent Prompt Builder (`agents/prompts.py`)

- [ ] `build_system_prompt(persona, phase_mandate, guidelines) -> str`
- [ ] `build_user_prompt(posts, phase_signal, knowledge) -> str`
- [ ] Phase mandate selection based on current phase
- [ ] Agent personas loaded from config/AGENT_PROMPTS.md content

**Tests**:
- Prompt includes persona, correct phase mandate, and guidelines
- Phase change produces different mandate in prompt
- Prompt length within expected token bounds

**Success criteria**: Prompts compose correctly for all 6 agents x 4 phases = 24 combinations.

### Step 2.3 — Base Deliberation Agent (`agents/base.py`)

- [ ] `BaseDeliberationAgent` class
- [ ] `should_respond(posts, phase) -> (bool, list[str])` delegates to TriggerEvaluator
- [ ] `generate_post(deps) -> Post` calls LLM and parses response
- [ ] `AgentDependencies` dataclass (session, phase, posts, knowledge context)
- [ ] All 6 agent configs instantiable from YAML + prompts

**Tests**:
- Agent defers to trigger evaluator for should_respond
- Agent builds correct prompt and calls LLM
- Agent parses LLM response into valid Post model
- Malformed LLM response handled gracefully (fallback post)

**Success criteria**: Each agent produces valid posts when triggered.

### Step 2.4 — Deliberation Engine (`engine.py`)

- [ ] `EmergentDeliberationEngine` class
- [ ] Seed phase: all agents produce initial posts
- [ ] Main loop: Observer → termination check → trigger eval → response generation → update
- [ ] `run_deliberation()` async generator yielding Post, PhaseSignal, EnergyUpdate
- [ ] Human intervention handling
- [ ] Graceful degradation (agent failure doesn't block deliberation)

**Tests**:
- Seed phase produces 6 posts (one per agent)
- Main loop runs and terminates (mock LLM, energy decay)
- Phase transitions occur during deliberation
- At least 12 posts before termination (min_posts guard)
- Maximum turns cap works
- Agent failure → continue with remaining agents
- Human intervention injects energy

**Success criteria**: Full deliberation runs mock-to-completion. Produces 12-30 posts with phase transitions and energy-based termination.

### Step 2.5 — End-to-End Integration Test

- [ ] Single integration test: hypothesis in → ConsensusMap out
- [ ] Verify posts contain diverse stances
- [ ] Verify phase transitions occurred
- [ ] Verify energy declined toward termination
- [ ] Verify Red Team challenged consensus
- [ ] Run with multiple mock LLM behaviors to test robustness

**Success criteria**: Complete deliberation produces coherent output with expected emergent properties.

---

## Phase 3: API & Real LLM Integration (Make It Fast)

**Goal**: Working API with real LLM, ready for frontend.

### Step 3.1 — FastAPI Application (`api/`)

- [ ] `POST /api/deliberations` — create session
- [ ] `POST /api/deliberations/{id}/start` — start with SSE streaming
- [ ] `POST /api/deliberations/{id}/intervene` — human intervention
- [ ] `GET /api/deliberations/{id}` — get session state
- [ ] `GET /api/deliberations/{id}/energy` — energy history
- [ ] WebSocket endpoint for real-time updates

**Tests**:
- API creates session and returns ID
- Start streams posts as SSE events
- Intervention returns response posts
- Get session returns current state
- WebSocket connects and receives events
- Error responses for invalid session IDs

**Success criteria**: All endpoints work, streaming produces events in real-time.

### Step 3.2 — Real LLM Integration

- [ ] Anthropic Claude adapter implementing `LLMInterface`
- [ ] Structured output parsing (JSON mode or tool use)
- [ ] Retry logic with exponential backoff for rate limits
- [ ] Token usage tracking
- [ ] `LLM_MODE=mock|real` environment switch

**Tests**:
- Integration test with real LLM (marked slow, optional in CI)
- Retry logic works on simulated rate limit
- Structured output correctly parsed into Post model

**Success criteria**: Full deliberation runs with real Claude API.

### Step 3.3 — Database Persistence (deferred)

> **Note**: Database is deferred. In-memory state is sufficient for Phase 1-2
> and most of Phase 3. Add PostgreSQL when session persistence across
> restarts is needed.

- [ ] SQLAlchemy models matching schema from SYSTEM_DESIGN.md
- [ ] Session, Post, EnergyHistory, ConsensusMap tables
- [ ] Alembic migrations
- [ ] Repository pattern abstracting storage

---

## Testing Strategy

### Test Pyramid

```
         ┌──────────────┐
         │  Behavioral  │  ← Emergent property tests (2-3)
         │    Tests     │
         ├──────────────┤
         │ Integration  │  ← Full deliberation loop (3-5)
         │    Tests     │
         ├──────────────┤
         │  Unit Tests  │  ← Per-component (50+)
         └──────────────┘
```

### Unit Tests (per component)

| Component | Key Test Cases | Count |
|-----------|---------------|-------|
| Models | Validation, serialization, factories | ~8 |
| Energy | Each component, clamping, termination | ~10 |
| Observer | Phase detection, hysteresis, confidence, meta-obs | ~12 |
| Triggers | Each rule, phase modulation, refractory, Red Team | ~15 |
| Config | Loading, defaults, overrides, validation | ~5 |
| Agent | Prompt build, trigger delegation, post generation | ~8 |
| Engine | Seed, loop, termination, intervention, degradation | ~8 |

### Integration Tests

| Test | What It Validates |
|------|-------------------|
| Full mock deliberation | Engine produces valid output end-to-end |
| Contentious hypothesis | Extended debate, higher turn count |
| Quick consensus | Red Team fires, prevents shallow convergence |
| Human intervention | Energy injection extends deliberation |
| Agent failure | Graceful degradation, remaining agents continue |

### Behavioral Tests (Emergent Properties)

These validate the system's emergent behavior — the "magic" of the design:

| Test | What It Validates |
|------|-------------------|
| Red Team prevents premature consensus | 3+ supportive posts → Red Team responds |
| Bridge opportunities emerge | Agents with overlapping domains find connections |
| Energy naturally decays | Repetitive mock responses → energy drops → termination |
| Phase transitions are stable | Hysteresis prevents oscillation under noisy metrics |

### Test Infrastructure

- **Fixtures**: `create_post()`, `create_session()`, `create_agent()` factories with sensible defaults and overrides
- **Mock LLM modes**: `always_supportive`, `always_critical`, `mixed`, `high_novelty`, `low_novelty`, `declining`
- **Markers**: `@pytest.mark.slow` for real LLM tests, `@pytest.mark.integration` for full-loop tests

---

## Verification & Success Criteria

### Phase 1 Gate (Core Logic)

| Criteria | Metric |
|----------|--------|
| All unit tests pass | `pytest tests/test_energy.py tests/test_observer.py tests/test_triggers.py tests/test_models.py` green |
| Energy formula calibrated | Healthy deliberation mock produces energy curve matching ENERGY_MODEL.md |
| Observer detects all 4 phases | Truth table from OBSERVER_SPEC.md satisfied |
| Triggers fire correctly | Each of 9 trigger rules validated independently |
| No external dependencies | Tests run with no API keys, no database, no network |

### Phase 2 Gate (Working Loop)

| Criteria | Metric |
|----------|--------|
| Full deliberation completes | Mock deliberation produces 12-30 posts, ends with synthesis |
| Phase transitions occur | At least 2 phase transitions in a typical run |
| Red Team engages | Red Team responds at least once when consensus forms |
| Energy terminates naturally | Energy drops below 0.2 for 3 consecutive turns |
| Multiple mock scenarios pass | Contentious, quick-consensus, and intervention scenarios all work |

### Phase 3 Gate (API Ready)

| Criteria | Metric |
|----------|--------|
| API endpoints functional | All REST endpoints return correct responses |
| Streaming works | SSE/WebSocket delivers posts in real-time |
| Real LLM deliberation | End-to-end deliberation with Claude produces coherent output |
| Configuration-driven | Changing YAML config alters behavior without code changes |

### Overall Success Metrics (from docs/README.md)

| Metric | Target | How We Measure |
|--------|--------|----------------|
| Agent trigger accuracy | >80% valuable posts | Review posts from mock + real runs; rate "valuable" |
| Phase detection accuracy | >70% human agreement | Annotate 10+ runs; compare Observer vs human labels |
| Serendipity emergence | Novel connections without forcing | Bridge trigger fires, produces non-obvious connections |
| Conversation naturalness | Reduced repetition vs fixed-schedule | Compare staleness scores: emergent vs round-robin |
| Energy termination | Synthesis at appropriate time | Energy curves match healthy pattern from ENERGY_MODEL.md |

---

## Implementation Order & Dependencies

```
Step 1.1  Scaffolding
  │
  ├── Step 1.2  Models ──────────────────────────┐
  │     │                                         │
  │     ├── Step 1.3  Energy Calculator           │
  │     │                                         │
  │     ├── Step 1.4  Observer Agent              │
  │     │                                         │
  │     └── Step 1.5  Trigger Evaluator           │
  │                                               │
  │   Step 1.6  Configuration ────────────────────┤
  │                                               │
  ├── Step 2.1  LLM Interface & Mock ─────────────┤
  │                                               │
  ├── Step 2.2  Prompt Builder ───────────────────┤
  │                                               │
  └── Step 2.3  Base Agent ───────────────────────┘
        │
        └── Step 2.4  Deliberation Engine
              │
              ├── Step 2.5  Integration Tests
              │
              ├── Step 3.1  FastAPI Application
              │
              └── Step 3.2  Real LLM Integration
```

Steps 1.3, 1.4, and 1.5 can be built in parallel — they all depend on models but not on each other.

---

## Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Language | Python 3.11+ | Async support, LLM ecosystem, spec compatibility |
| Models | Pydantic v2 | Validation, serialization, config; already in spec |
| API | FastAPI | Async, WebSocket support, Pydantic integration |
| Testing | pytest + pytest-asyncio | Standard, fixtures, async test support |
| LLM | Anthropic SDK | Primary LLM target from spec |
| Config | PyYAML + Pydantic | YAML files validated through Pydantic models |
| Task runner | None (pytest + scripts) | Keep simple until needed |

### Dependencies by Phase

**Phase 1** (zero external services):
- pydantic
- pyyaml
- pytest, pytest-asyncio

**Phase 2** (still no external services):
- (same as Phase 1)

**Phase 3** (external services):
- fastapi, uvicorn
- anthropic
- httpx (test client)
- websockets

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM output unparseable | Agent produces invalid Post | Structured output with fallback parsing; mock-first development |
| Energy never terminates | Infinite loop | Hard cap at max_turns; integration tests verify termination |
| Phase oscillation | Confusing agent behavior | Hysteresis with tunable threshold; behavioral tests |
| Trigger rules too noisy | Agents over-respond | Refractory period; phase modulation; integration test monitoring |
| Trigger rules too quiet | Agents under-respond | Silence-breaking rule as safety net; min-responders in engine |

---

## What's Explicitly Out of Scope

- Frontend (Next.js) — deferred until API is stable
- Database persistence — in-memory first; add when needed
- Knowledge service / RAG / pgvector — stub interface, implement later
- Monitoring / Prometheus metrics — add after core works
- Docker / deployment — local development first
- Authentication / multi-tenancy

---

*Plan created: 2026-02-10*
*Colloquip v0.1 — Emergent Deliberation System*
