# Colloquip: Implementation Plan

## Context: Hackathon Constraints

**Event**: Built with Opus 4.6 — Claude Code Hackathon (Cerebral Valley + Anthropic)
**Timeline**: Feb 10-16, 2026 (6 days). Submissions due Feb 16 at 3:00 PM EST.
**Resources**: $500 in Claude API credits, max 2 team members.
**Deliverables**: Open source GitHub repo + project description + **video** (most important).
**Judging criteria**: Technical innovation, implementation quality, potential impact.
**Key insight**: "Judges favor functional prototypes over extensive documentation."

---

## Guiding Principles

1. **Make it work** → **Make it right** → **Make it fast**
2. **Demo-driven development** — every day should end with something runnable
3. Every component testable in isolation with no LLM calls required
4. Interfaces first, implementations second — enables pivoting
5. Configuration-driven behavior — change tuning without code changes
6. Minimal dependencies — add only what's needed at each phase
7. **Budget API credits** — mock-first, real LLM only for integration + demo

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
│       │   ├── mock.py        # Mock LLM for testing
│       │   └── anthropic.py   # Real Claude adapter
│       ├── api/
│       │   ├── __init__.py
│       │   ├── app.py         # FastAPI application
│       │   ├── routes.py      # REST endpoints
│       │   └── ws.py          # WebSocket endpoint
│       └── cli.py             # CLI demo runner (rich terminal output)
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
├── plan/
│   └── IMPLEMENTATION_PLAN.md
├── pyproject.toml
├── LICENSE                    # MIT License (open source requirement)
└── README.md
```

---

## Day-by-Day Schedule

### Day 1 (Feb 10) — Foundation: Models + Pure Logic

**Goal**: All core data models and pure-function business logic working with tests.

| Block | Task | Deliverable |
|-------|------|-------------|
| Morning | Project scaffolding (Step 1.1) | `pyproject.toml`, package structure, pytest green |
| Morning | Data models (Step 1.2) | All Pydantic models + test factories |
| Afternoon | Energy calculator (Step 1.3) | `energy.py` with full test coverage |
| Afternoon | Observer agent (Step 1.4) | `observer.py` with hysteresis + tests |
| Evening | Trigger evaluator (Step 1.5) | `triggers.py` with all 9 rules + tests |
| Evening | Configuration (Step 1.6) | YAML config loading, defaults |

**End-of-day checkpoint**: `pytest` passes with ~40 unit tests. All pure logic works.

### Day 2 (Feb 11) — Agent Framework + Mock Deliberation Loop

**Goal**: Full deliberation runs end-to-end with mock LLM.

| Block | Task | Deliverable |
|-------|------|-------------|
| Morning | LLM interface + mock (Step 2.1) | `MockLLM` with configurable behaviors |
| Morning | Prompt builder (Step 2.2) | Persona + phase mandate composition |
| Afternoon | Base agent (Step 2.3) | All 6 agents instantiable, trigger-aware |
| Afternoon | Deliberation engine (Step 2.4) | Main loop: seed → emergent → termination |
| Evening | Integration tests (Step 2.5) | Full mock deliberation passes |

**End-of-day checkpoint**: `python -m colloquip.cli --mode mock` runs a complete deliberation and prints results to terminal.

### Day 3 (Feb 12) — Real LLM + CLI Demo

**Goal**: Real Claude-powered deliberation running with rich terminal output.

| Block | Task | Deliverable |
|-------|------|-------------|
| Morning | Claude adapter (Step 3.2) | Real LLM integration with structured output |
| Morning | First real deliberation run | Verify output quality, tune prompts |
| Afternoon | CLI demo runner (`cli.py`) | Rich terminal UI: color-coded agents, phase indicator, energy bar |
| Evening | Prompt tuning | Adjust prompts based on real output quality |

**End-of-day checkpoint**: `python -m colloquip.cli "GLP-1 agonists improve cognitive function"` runs a full real deliberation with compelling terminal output.

**API credit budget**: ~$50-75 for Day 3 testing (5-8 full runs).

### Day 4 (Feb 13) — API + Streaming

**Goal**: FastAPI backend serving deliberations with real-time streaming.

| Block | Task | Deliverable |
|-------|------|-------------|
| Morning | FastAPI application (Step 3.1) | REST endpoints + SSE streaming |
| Afternoon | WebSocket endpoint | Real-time deliberation updates |
| Evening | API integration tests | All endpoints verified |

**End-of-day checkpoint**: `curl` or simple client can start a deliberation and receive streaming posts.

### Day 5 (Feb 14) — Polish + Edge Cases

**Goal**: Robust, demo-ready system. Handle failures gracefully.

| Block | Task | Deliverable |
|-------|------|-------------|
| Morning | Error handling & edge cases | Graceful degradation, retry logic |
| Afternoon | Config tuning | Run 3-5 deliberations, tune energy/trigger thresholds |
| Afternoon | README polish | Sell innovation + impact for judges |
| Evening | Behavioral tests | Validate emergent properties with real LLM |

**End-of-day checkpoint**: System handles failures gracefully. 3+ successful real deliberation runs saved.

**API credit budget**: ~$100-150 for Day 5 tuning runs.

### Day 6 (Feb 15-16) — Video + Submission

**Goal**: Compelling demo video. Clean submission.

| Block | Task | Deliverable |
|-------|------|-------------|
| Morning (Feb 15) | Plan video script | Outline: problem → approach → demo → results |
| Afternoon (Feb 15) | Record demo | Screen recording of live deliberation (CLI or API) |
| Evening (Feb 15) | Edit video | Clean cuts, narration, highlight emergent moments |
| Morning (Feb 16) | Final polish | README, repo cleanup, any last fixes |
| By 3pm EST (Feb 16) | **Submit** | GitHub repo + video + description |

**Video strategy**: Show a real deliberation running live. Highlight:
- Agents self-selecting when to speak (not scheduled)
- Phase transitions emerging from conversation dynamics
- Red Team challenging premature consensus
- Energy naturally declining toward synthesis
- The "aha moment" when a bridge connection emerges

**API credit budget**: ~$50 for final demo recordings.

---

## Phase 1: Core Domain Models & Pure Logic (Day 1)

**Goal**: All core business logic works, fully tested, zero external dependencies.

### Step 1.1 — Project Scaffolding

- [ ] `pyproject.toml` with Python 3.11+, pytest, pydantic, pyyaml
- [ ] Basic package structure (`src/colloquip/`)
- [ ] Test infrastructure (`tests/`, conftest with factories)
- [ ] `LICENSE` (MIT)
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

## Phase 2: Agent Framework & Deliberation Loop (Day 2)

**Goal**: Full deliberation loop runs end-to-end with mock LLM. CLI prints results.

### Step 2.1 — LLM Interface & Mock (`llm/`)

- [ ] `LLMInterface` protocol (abstract base)
- [ ] `MockLLM` implementation that returns deterministic, configurable responses
- [ ] Mock returns structured output matching `Post` fields (stance, claims, questions, novelty)
- [ ] Configurable mock behaviors (always supportive, always critical, mixed, declining novelty)

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

### Step 2.5 — CLI Runner + End-to-End Integration Tests

- [ ] `cli.py` — basic terminal output of deliberation (agent name, phase, content)
- [ ] Single integration test: hypothesis in → ConsensusMap out
- [ ] Verify posts contain diverse stances
- [ ] Verify phase transitions occurred
- [ ] Verify energy declined toward termination
- [ ] Verify Red Team challenged consensus

**Success criteria**: `python -m colloquip.cli --mode mock "hypothesis"` runs and prints a complete deliberation. Integration tests green.

---

## Phase 3: Real LLM + API + Demo Polish (Days 3-5)

**Goal**: Real Claude deliberation, API with streaming, demo-ready CLI.

### Step 3.1 — Real LLM Integration (Day 3 morning)

- [ ] Anthropic Claude adapter implementing `LLMInterface`
- [ ] Structured output parsing (JSON mode or tool use)
- [ ] Retry logic with exponential backoff for rate limits
- [ ] Token usage tracking and logging
- [ ] `LLM_MODE=mock|real` environment switch

**Tests**:
- Integration test with real LLM (marked `@pytest.mark.slow`)
- Retry logic works on simulated rate limit
- Structured output correctly parsed into Post model

**Success criteria**: Full deliberation runs with real Claude API.

### Step 3.2 — CLI Demo Runner (Day 3 afternoon)

- [ ] Rich terminal output: color-coded agents, phase indicator, energy bar
- [ ] Real-time streaming display as posts are generated
- [ ] Summary display at end (ConsensusMap)
- [ ] `--mode mock|real` flag
- [ ] `--hypothesis "..."` argument
- [ ] `--save-transcript path` for recording runs

**Success criteria**: Visually compelling terminal demo suitable for video recording.

### Step 3.3 — FastAPI Application (Day 4)

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
- Error responses for invalid session IDs

**Success criteria**: All endpoints work, streaming produces events in real-time.

### Step 3.4 — Polish & Tuning (Day 5)

- [ ] Error handling & graceful degradation
- [ ] Run 3-5 real deliberations, tune energy/trigger thresholds
- [ ] Behavioral tests with real LLM output
- [ ] README: sell innovation + impact (see "README for Judges" below)
- [ ] Repo cleanup: remove dead code, ensure clean `git log`

**Success criteria**: System handles failures gracefully. Multiple successful real deliberation runs.

### Step 3.5 — Database Persistence (stretch goal, only if time)

> **Note**: Database is deferred. In-memory state is sufficient for demo.
> Only add if time permits on Day 5.

- [ ] SQLAlchemy models matching schema from SYSTEM_DESIGN.md
- [ ] Repository pattern abstracting storage

---

## Video Strategy (Day 6)

The video is the **most important submission artifact**. Plan it deliberately.

### Video Outline (~3-5 minutes)

1. **Hook** (30s): "What if scientific debates could happen autonomously — and produce insights no single agent planned?"
2. **Problem** (30s): Current multi-agent systems use fixed schedules. Conversations are artificial.
3. **Our approach** (60s): Emergent behavior from simple rules. Show the architecture diagram. Explain cellular-automata inspiration.
4. **Live demo** (90s): Run a real deliberation. Show:
   - Agents self-selecting (trigger rules visible)
   - Phase transition (EXPLORE → DEBATE)
   - Red Team breaking consensus
   - Energy curve declining toward synthesis
   - A bridge connection emerging
5. **Results** (30s): ConsensusMap output. Highlight a serendipitous finding.
6. **Impact** (30s): Applications beyond drug discovery. Any domain needing structured multi-expert deliberation.

### Recording Tips

- Use the CLI demo runner with rich formatting — more visual than raw API
- Have a compelling hypothesis ready (something that generates real debate)
- Do a dry run first with mock to verify timing
- Record the real run — authenticity > polish

---

## API Credit Budget

Total: $500 in Claude API credits.

| Activity | Estimated Cost | Day |
|----------|---------------|-----|
| First real LLM test (3-5 runs) | $50-75 | Day 3 |
| Prompt tuning iterations (5-8 runs) | $75-100 | Day 3-4 |
| Threshold tuning (3-5 runs) | $50-75 | Day 5 |
| Video demo recordings (3-5 runs) | $50-75 | Day 6 |
| Buffer for retries and debugging | $50-75 | Throughout |
| **Reserved unspent** | **~$100-150** | — |

**Cost controls**:
- Use mock mode for ALL development and unit/integration testing
- Track token usage per run in logs
- Use `claude-sonnet` for development; switch to `opus-4-6` for final demo only if budget allows
- Reduce `max_turns` to 15 during development (halves cost per run)

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

### Day 1 Gate (Core Logic)

| Criteria | Metric |
|----------|--------|
| All unit tests pass | `pytest tests/test_energy.py tests/test_observer.py tests/test_triggers.py tests/test_models.py` green |
| Energy formula calibrated | Healthy deliberation mock produces energy curve matching ENERGY_MODEL.md |
| Observer detects all 4 phases | Truth table from OBSERVER_SPEC.md satisfied |
| Triggers fire correctly | Each of 9 trigger rules validated independently |
| No external dependencies | Tests run with no API keys, no database, no network |

### Day 2 Gate (Working Loop)

| Criteria | Metric |
|----------|--------|
| Full deliberation completes | Mock deliberation produces 12-30 posts, ends with synthesis |
| Phase transitions occur | At least 2 phase transitions in a typical run |
| Red Team engages | Red Team responds at least once when consensus forms |
| Energy terminates naturally | Energy drops below 0.2 for 3 consecutive turns |
| CLI runs | `python -m colloquip.cli --mode mock` produces readable output |

### Day 3 Gate (Real LLM)

| Criteria | Metric |
|----------|--------|
| Real deliberation completes | End-to-end with Claude produces coherent posts |
| CLI demo works | Rich terminal output shows agents, phases, energy in real-time |
| Output quality | Agents stay in character, phase mandates influence behavior |

### Day 4 Gate (API)

| Criteria | Metric |
|----------|--------|
| API endpoints functional | All REST endpoints return correct responses |
| Streaming works | SSE delivers posts in real-time |

### Day 5 Gate (Polish)

| Criteria | Metric |
|----------|--------|
| Error handling works | Agent failure → continue with remaining agents |
| Tuned thresholds | 3+ successful real deliberations with natural flow |
| README sells the project | Innovation + impact clearly articulated |

### Day 6 Gate (Submit)

| Criteria | Metric |
|----------|--------|
| Video complete | 3-5 minute video showing live demo |
| Repo clean | No dead code, clean git history, LICENSE present |
| Submitted before 3pm EST | All deliverables uploaded |

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
Day 1:
  Step 1.1  Scaffolding + LICENSE
    │
    ├── Step 1.2  Models ──────────────────────────┐
    │     │                                         │
    │     ├── Step 1.3  Energy Calculator           │  (parallel)
    │     ├── Step 1.4  Observer Agent              │  (parallel)
    │     └── Step 1.5  Trigger Evaluator           │  (parallel)
    │                                               │
    └── Step 1.6  Configuration ────────────────────┘

Day 2:
    ├── Step 2.1  LLM Interface & Mock ─────────────┐
    ├── Step 2.2  Prompt Builder ───────────────────┤
    └── Step 2.3  Base Agent ───────────────────────┘
          │
          └── Step 2.4  Deliberation Engine
                │
                └── Step 2.5  CLI Runner + Integration Tests

Day 3:
    ├── Step 3.1  Real LLM Integration
    └── Step 3.2  CLI Demo Runner (rich output)

Day 4:
    └── Step 3.3  FastAPI Application

Day 5:
    └── Step 3.4  Polish, Tuning, README

Day 6:
    └── Video + Submission
```

---

## Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Language | Python 3.11+ | Async support, LLM ecosystem, spec compatibility |
| Models | Pydantic v2 | Validation, serialization, config; already in spec |
| API | FastAPI | Async, WebSocket support, Pydantic integration |
| Testing | pytest + pytest-asyncio | Standard, fixtures, async test support |
| LLM | Anthropic SDK | Primary LLM target; hackathon sponsor |
| Config | PyYAML + Pydantic | YAML files validated through Pydantic models |
| CLI | rich (Python) | Color-coded terminal output for demo |

### Dependencies by Phase

**Day 1-2** (zero external services):
- pydantic
- pyyaml
- pytest, pytest-asyncio

**Day 3** (LLM calls):
- anthropic
- rich

**Day 4** (API):
- fastapi, uvicorn
- httpx (test client)

---

## README for Judges

The root README must sell the project. Structure:

1. **One-line pitch**: "Emergent multi-agent deliberation — where serendipity arises from simple rules, not engineered detection."
2. **The insight**: Inspired by cellular automata. Simple local rules produce complex global behavior.
3. **What makes this different**: Side-by-side comparison table (fixed-schedule vs emergent).
4. **Quick demo**: GIF or screenshot of terminal output showing a deliberation in progress.
5. **How to run**: `pip install -e .` → `python -m colloquip.cli "your hypothesis"`.
6. **Architecture**: Brief diagram showing Observer + Agents + Energy loop.
7. **Technical highlights**: Trigger rules, hysteresis, energy-based termination.
8. **Link to video**.

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM output unparseable | Agent produces invalid Post | Structured output with fallback parsing; mock-first dev |
| Energy never terminates | Infinite loop | Hard cap at max_turns; integration tests verify termination |
| Phase oscillation | Confusing agent behavior | Hysteresis with tunable threshold; behavioral tests |
| Trigger rules too noisy | Agents over-respond | Refractory period; phase modulation; integration monitoring |
| Trigger rules too quiet | Agents under-respond | Silence-breaking rule as safety net; min-responders in engine |
| API credits run out | Can't demo with real LLM | Mock-first; track usage; reserve $100+ for final demo |
| Video not compelling | Weak submission | Plan video on Day 5, record Day 6 morning; dry run first |
| Run out of time | Incomplete submission | Day-by-day gates ensure something submittable every day |

---

## What's Explicitly Out of Scope

- Frontend (Next.js) — CLI demo is sufficient for hackathon video
- Database persistence — in-memory state is sufficient for demo
- Knowledge service / RAG / pgvector — stub interface, implement later
- Monitoring / Prometheus metrics — not needed for hackathon
- Docker / deployment — local development only
- Authentication / multi-tenancy

---

*Plan created: 2026-02-10*
*Updated: 2026-02-10 (hackathon constraints integrated)*
*Colloquip v0.1 — Emergent Deliberation System*
