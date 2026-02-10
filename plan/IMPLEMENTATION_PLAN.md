# Colloquip: Implementation Plan

## Context

**Event**: Built with Opus 4.6 — Claude Code Hackathon (Cerebral Valley + Anthropic)
**Deliverables**: Open source GitHub repo + project description + **video** (most important).
**Judging criteria**: Technical innovation, implementation quality, potential impact.
**Key insight**: "Judges favor functional prototypes over extensive documentation."

---

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
│       │   ├── mock.py        # Mock LLM for testing
│       │   └── anthropic.py   # Real Claude adapter
│       ├── api/
│       │   ├── __init__.py
│       │   ├── app.py         # FastAPI application
│       │   ├── routes.py      # REST endpoints
│       │   └── ws.py          # WebSocket endpoint
│       └── cli.py             # CLI runner (rich terminal output)
├── web/                       # Deliberation Dashboard (React SPA)
│   ├── package.json
│   ├── tsconfig.json
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── hooks/
│   │   │   └── useDeliberation.ts   # WebSocket connection + state
│   │   ├── components/
│   │   │   ├── AgentRoster.tsx       # Left panel: agent status + triggers
│   │   │   ├── ConversationStream.tsx # Center: posts with agent colors
│   │   │   ├── EnergyChart.tsx       # Right: real-time energy curve
│   │   │   ├── PhaseTimeline.tsx     # Right: phase progression indicator
│   │   │   ├── TriggerLog.tsx        # Bottom: why each agent spoke
│   │   │   ├── ConsensusView.tsx     # Final synthesis display
│   │   │   ├── ControlBar.tsx        # Top: hypothesis input, start/stop
│   │   │   └── HumanIntervention.tsx # Intervention input modal
│   │   ├── types/
│   │   │   └── deliberation.ts       # TypeScript types matching Python models
│   │   └── utils/
│   │       └── colors.ts             # Agent color assignments
│   └── public/
│       └── favicon.svg
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

## Phase 1: Core Domain Models & Pure Logic

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

### Phase 1 Gate

| Criteria | Metric |
|----------|--------|
| All unit tests pass | `pytest tests/test_energy.py tests/test_observer.py tests/test_triggers.py tests/test_models.py` green |
| Energy formula calibrated | Healthy deliberation mock produces energy curve matching ENERGY_MODEL.md |
| Observer detects all 4 phases | Truth table from OBSERVER_SPEC.md satisfied |
| Triggers fire correctly | Each of 9 trigger rules validated independently |
| No external dependencies | Tests run with no API keys, no database, no network |

---

## Phase 2: Agent Framework & Deliberation Loop

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

### Phase 2 Gate

| Criteria | Metric |
|----------|--------|
| Full deliberation completes | Mock deliberation produces 12-30 posts, ends with synthesis |
| Phase transitions occur | At least 2 phase transitions in a typical run |
| Red Team engages | Red Team responds at least once when consensus forms |
| Energy terminates naturally | Energy drops below 0.2 for 3 consecutive turns |
| CLI runs | `python -m colloquip.cli --mode mock` produces readable output |

---

## Phase 3: Real LLM Integration & CLI Polish

**Goal**: Real Claude-powered deliberation with rich terminal output.

### Step 3.1 — Real LLM Integration

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

### Step 3.2 — CLI Demo Runner

- [ ] Rich terminal output: color-coded agents, phase indicator, energy bar
- [ ] Real-time streaming display as posts are generated
- [ ] Summary display at end (ConsensusMap)
- [ ] `--mode mock|real` flag
- [ ] `--hypothesis "..."` argument
- [ ] `--save-transcript path` for recording runs

**Success criteria**: Visually compelling terminal demo suitable for video recording.

### Step 3.3 — Prompt Tuning & Threshold Calibration

- [ ] Run real deliberations and evaluate output quality
- [ ] Tune agent personas for distinct, authentic voices
- [ ] Calibrate energy thresholds against real LLM output
- [ ] Calibrate trigger sensitivity (too noisy vs too quiet)
- [ ] Verify Red Team fires and produces meaningful challenges
- [ ] Verify bridge connections produce non-obvious insights

**Success criteria**: 5+ successful real deliberation runs with natural flow, diverse stances, and coherent synthesis.

### Phase 3 Gate

| Criteria | Metric |
|----------|--------|
| Real deliberation completes | End-to-end with Claude produces coherent posts |
| CLI demo works | Rich terminal output shows agents, phases, energy in real-time |
| Output quality | Agents stay in character, phase mandates influence behavior |
| Thresholds tuned | Energy curve and trigger frequency match design intent |

---

## Phase 4: API Layer

**Goal**: FastAPI backend with real-time streaming, ready for the web dashboard.

### Step 4.1 — FastAPI Application (`api/`)

- [ ] `POST /api/deliberations` — create session with hypothesis
- [ ] `POST /api/deliberations/{id}/start` — start with SSE streaming
- [ ] `POST /api/deliberations/{id}/intervene` — human intervention
- [ ] `GET /api/deliberations/{id}` — get session state (posts, phase, energy)
- [ ] `GET /api/deliberations/{id}/energy` — energy history as time series

**Tests**:
- API creates session and returns ID
- Start streams posts as SSE events
- Intervention returns response posts
- Get session returns current state
- Error responses for invalid session IDs

**Success criteria**: All REST endpoints work, SSE streaming produces events in real-time.

### Step 4.2 — WebSocket Endpoint (`api/ws.py`)

The web dashboard requires richer real-time data than SSE provides. The WebSocket streams typed events that map directly to dashboard components.

- [ ] WebSocket connection at `/ws/deliberations/{id}`
- [ ] Event types sent over WebSocket:
  - `post` — new agent post (agent, stance, content, claims, questions)
  - `phase_change` — phase transition (from, to, confidence, observation)
  - `energy_update` — energy value + component breakdown (novelty, disagreement, questions, staleness)
  - `trigger_fired` — agent trigger activation (agent, rule, reason)
  - `agent_status` — agent state change (active, refractory, idle)
  - `session_complete` — deliberation finished (consensus map, final energy)
- [ ] Backpressure handling for slow clients
- [ ] Reconnection support (send missed events from sequence number)

**Tests**:
- WebSocket connects and receives typed events
- All event types serialized correctly
- Reconnection replays missed events
- Multiple concurrent clients receive same events

**Success criteria**: WebSocket streams all event types needed by the dashboard in real-time.

### Phase 4 Gate

| Criteria | Metric |
|----------|--------|
| API endpoints functional | All REST endpoints return correct responses |
| SSE streaming works | SSE delivers posts in real-time |
| WebSocket streams all event types | All 6 event types delivered to connected clients |
| Reconnection works | Client reconnecting receives missed events |

---

## Phase 5: Web Dashboard — Deliberation Visualization

**Goal**: A single-page React app that makes the invisible emergence visible. The dashboard is the primary demo artifact — it shows what no chat interface can: *why* agents speak, *how* energy flows, and *when* phases shift.

### Design Philosophy

The dashboard is a **simulation control panel**, not a chat app. Its job is to surface the emergent dynamics that happen behind the scenes:

```
┌─────────────────────────────────────────────────────────────────┐
│  COLLOQUIP                                         ▶ Start      │
│  Hypothesis: [GLP-1 agonists improve cognitive function     ]   │
├────────────┬───────────────────────────────┬────────────────────┤
│  AGENTS    │  CONVERSATION                 │  DYNAMICS          │
│            │                               │                    │
│  ● Bio     │  ┌─────────────────────────┐  │  Energy            │
│    Chem    │  │ Dr. Vasquez (Biology)    │  │  0.82 ████████░░  │
│  ● ADMET   │  │ EXPLORE · SUPPORTIVE    │  │                    │
│    Clinic  │  │ GLP-1 agonists share a  │  │  ┌──────────────┐ │
│    Reg     │  │ notable structural...    │  │  │  /\    /\    │ │
│    RedTm   │  │ 🔗 relevance            │  │  │ /  \  /  \_  │ │
│            │  └─────────────────────────┘  │  │/    \/     \  │ │
│  Status:   │                               │  └──────────────┘ │
│  Bio  ●act │  ┌─────────────────────────┐  │                    │
│  Chem ○ref │  │ Dr. Okafor (Red Team)   │  │  Phase             │
│  ADME ●act │  │ DEBATE · CRITICAL       │  │  ■ EXPLORE         │
│  Clin ○idl │  │ The consensus is        │  │  □ DEBATE          │
│  Reg  ○idl │  │ premature — consider... │  │  □ DEEPEN          │
│  RedT ●act │  │ ⚡ consensus_forming     │  │  □ CONVERGE        │
│            │  └─────────────────────────┘  │  □ SYNTHESIS        │
├────────────┴───────────────────────────────┴────────────────────┤
│  TRIGGER LOG                                                     │
│  14:23:01  Dr. Okafor fired [consensus_forming] — 3+            │
│            supportive posts without criticism                     │
│  14:22:48  Dr. Vasquez fired [relevance] — GLP-1 in domain      │
│  14:22:30  Dr. Kim fired [bridge_opportunity] — receptor         │
│            binding overlaps Bio + Chem domains                    │
└─────────────────────────────────────────────────────────────────┘
```

### Step 5.1 — Project Setup & WebSocket Hook

- [ ] Vite + React + TypeScript project in `web/`
- [ ] TypeScript types matching Python Pydantic models (`types/deliberation.ts`)
- [ ] `useDeliberation` hook: WebSocket connection, event dispatch, reconnection
- [ ] Connection state management (connecting, connected, disconnected, error)
- [ ] Mock WebSocket mode for UI development without running backend

**Tests**:
- Hook connects to WebSocket and dispatches events to state
- Reconnection attempts on disconnect
- Mock mode produces realistic event stream

**Success criteria**: `useDeliberation("session-id")` returns typed, reactive state that updates in real-time.

### Step 5.2 — Layout Shell & Control Bar

- [ ] Three-column responsive layout (agents | conversation | dynamics)
- [ ] `ControlBar` component: hypothesis text input, Start/Stop button, mode selector (mock/real)
- [ ] Session creation flow: enter hypothesis → create via API → connect WebSocket → start
- [ ] Loading and error states

**Success criteria**: User can type a hypothesis, hit Start, and see the session begin.

### Step 5.3 — Conversation Stream

The center panel — the actual deliberation content.

- [ ] `ConversationStream` component: scrollable list of posts
- [ ] Each post card shows:
  - Agent name + color badge
  - Current phase tag
  - Stance indicator (supportive/critical/neutral/novel)
  - Post content (markdown rendered)
  - Claims and questions (collapsible)
  - Trigger reason tag (which rule fired, subtle)
- [ ] Auto-scroll to latest post with manual scroll override
- [ ] Smooth entry animation for new posts
- [ ] Visual distinction between seed phase posts and emergent posts

**Success criteria**: Posts appear in real-time with clear agent attribution and stance. Easy to follow the deliberation flow.

### Step 5.4 — Agent Roster (Left Panel)

Shows the "life" of each agent — when they're active, when they're resting, when they're triggered.

- [ ] `AgentRoster` component: list of all 6 agents
- [ ] Per-agent display:
  - Name + domain + color
  - Status indicator: active (generating), refractory (cooling down), idle (waiting)
  - Post count
  - Last trigger rule that fired
- [ ] Pulse animation when agent is generating a response
- [ ] Dim appearance during refractory period
- [ ] Tooltip with full agent persona description

**Success criteria**: Glancing at the roster immediately shows who's active and why.

### Step 5.5 — Energy Chart (Right Panel, Top)

The "heartbeat" of the deliberation — makes energy dynamics tangible.

- [ ] `EnergyChart` component: real-time line chart (Recharts or Chart.js)
- [ ] X-axis: post number or turn. Y-axis: energy 0.0–1.0
- [ ] Energy line updates with each `energy_update` event
- [ ] Termination threshold line (dashed, at 0.2)
- [ ] Color gradient: green (healthy) → yellow (declining) → red (near termination)
- [ ] Energy component breakdown on hover (novelty, disagreement, questions, staleness)
- [ ] Energy injection spikes visually marked (when human intervenes)

**Success criteria**: Watching the energy chart tells the story of the deliberation — peaks during heated debate, valleys during consensus, injection spikes on intervention.

### Step 5.6 — Phase Timeline (Right Panel, Bottom)

- [ ] `PhaseTimeline` component: vertical list of all 5 phases
- [ ] Current phase highlighted, completed phases filled, future phases dimmed
- [ ] Transition markers showing when phase changed (at which post number)
- [ ] Observer confidence indicator for current phase
- [ ] Smooth transition animation

**Success criteria**: Phase progression is immediately legible. Transitions are visually satisfying.

### Step 5.7 — Trigger Log (Bottom Panel)

The "why" panel — this is what makes Colloquip's emergence visible. Without it, the dashboard is just a chat app.

- [ ] `TriggerLog` component: reverse-chronological log of trigger events
- [ ] Each entry shows: timestamp, agent name, trigger rule, reason string
- [ ] Color-coded by trigger type (relevance=blue, disagreement=red, bridge=purple, red-team=orange)
- [ ] Filterable by agent or trigger type
- [ ] Clickable entries scroll to the corresponding post in the conversation stream

**Success criteria**: A viewer can trace *why* each agent spoke by reading the trigger log. The emergent self-selection is demystified.

### Step 5.8 — Human Intervention & Consensus View

- [ ] `HumanIntervention` component: modal/drawer for injecting human input
  - Text input for human message
  - Shows current energy level and predicted boost
  - Submit sends to API intervention endpoint
- [ ] `ConsensusView` component: displayed when deliberation completes
  - Key findings
  - Areas of agreement and disagreement
  - Confidence levels
  - Recommended next steps
  - Final energy curve summary

**Success criteria**: Human can intervene mid-deliberation. Completion shows a meaningful synthesis.

### Step 5.9 — Polish & Responsiveness

- [ ] Dark mode (default for demo/video)
- [ ] Responsive layout (dashboard works at 1280px+ widths)
- [ ] Smooth animations throughout (framer-motion or CSS transitions)
- [ ] Keyboard shortcuts: Space to start/stop, Escape to close modals
- [ ] Sound effects (subtle, optional): soft chime on phase transition, alert on Red Team trigger

**Success criteria**: Dashboard feels polished and professional. Looks great in a screen recording.

### Phase 5 Gate

| Criteria | Metric |
|----------|--------|
| All components render | Dashboard shows agents, conversation, energy, phases, triggers |
| Real-time updates work | WebSocket events update all panels simultaneously |
| Energy chart animates | Smooth real-time line chart with component breakdown on hover |
| Trigger log traces decisions | Every agent post has a corresponding trigger log entry |
| Human intervention works | User can inject input and see energy spike |
| Consensus displays | Completion shows synthesis view |
| Video-ready | Dark mode, smooth animations, no visual bugs at 1280px+ |

---

## Phase 6: Database Persistence

**Goal**: Sessions persist across server restarts. Historical deliberations are retrievable.

### Step 6.1 — Database Models & Migrations

- [ ] SQLAlchemy models matching schema from SYSTEM_DESIGN.md
- [ ] `Session`, `Post`, `EnergyHistory`, `PhaseTransition`, `ConsensusMap` tables
- [ ] Alembic migrations
- [ ] Repository pattern abstracting storage (interface already used by engine)

### Step 6.2 — Session History

- [ ] `GET /api/deliberations` — list past sessions
- [ ] Session replay: load historical deliberation and step through it
- [ ] Dashboard: session picker / history sidebar

**Success criteria**: Server can restart without losing data. Past deliberations are browsable.

---

## Phase 7: Polish, Tuning & Submission Prep

**Goal**: Production-quality system ready for demo and submission.

### Step 7.1 — Error Handling & Robustness

- [ ] Graceful degradation on LLM failure (agent continues with fallback)
- [ ] WebSocket disconnect/reconnect handling
- [ ] API rate limit management
- [ ] Input validation on all endpoints

### Step 7.2 — Behavioral Tests (Emergent Properties)

These validate the system's emergent behavior — the "magic" of the design:

| Test | What It Validates |
|------|-------------------|
| Red Team prevents premature consensus | 3+ supportive posts → Red Team responds |
| Bridge opportunities emerge | Agents with overlapping domains find connections |
| Energy naturally decays | Repetitive responses → energy drops → termination |
| Phase transitions are stable | Hysteresis prevents oscillation under noisy metrics |

### Step 7.3 — README & Repo Polish

The root README must sell the project:

1. **One-line pitch**: "Emergent multi-agent deliberation — where serendipity arises from simple rules, not engineered detection."
2. **The insight**: Inspired by cellular automata. Simple local rules produce complex global behavior.
3. **What makes this different**: Side-by-side comparison (fixed-schedule vs emergent).
4. **Screenshot/GIF**: Dashboard showing a live deliberation.
5. **How to run**: Quick start instructions.
6. **Architecture**: Diagram showing Observer + Agents + Energy loop.
7. **Technical highlights**: Trigger rules, hysteresis, energy-based termination.
8. **Link to video**.

### Step 7.4 — Video Production

The video is the **most important submission artifact**.

**Video Outline (~3-5 minutes)**:

1. **Hook** (30s): "What if scientific debates could happen autonomously — and produce insights no single agent planned?"
2. **Problem** (30s): Current multi-agent systems use fixed schedules. Conversations are artificial.
3. **Our approach** (60s): Emergent behavior from simple rules. Show the architecture diagram. Cellular-automata inspiration.
4. **Live demo** (90s): Run a real deliberation in the dashboard. Show:
   - Agents self-selecting when to speak (trigger log visible)
   - Phase transition (EXPLORE → DEBATE) with animation
   - Red Team breaking consensus (energy spike)
   - Energy curve declining toward synthesis
   - A bridge connection emerging
5. **Results** (30s): ConsensusMap output. Highlight a serendipitous finding.
6. **Impact** (30s): Applications beyond drug discovery. Any domain needing structured multi-expert deliberation.

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

### Test Infrastructure

- **Fixtures**: `create_post()`, `create_session()`, `create_agent()` factories with sensible defaults and overrides
- **Mock LLM modes**: `always_supportive`, `always_critical`, `mixed`, `high_novelty`, `low_novelty`, `declining`
- **Markers**: `@pytest.mark.slow` for real LLM tests, `@pytest.mark.integration` for full-loop tests

---

## Implementation Order & Dependencies

```
Phase 1:  Scaffolding + LICENSE
  │
  ├── Models ──────────────────────────────┐
  │     │                                   │
  │     ├── Energy Calculator               │  (parallel)
  │     ├── Observer Agent                  │  (parallel)
  │     └── Trigger Evaluator               │  (parallel)
  │                                         │
  └── Configuration ────────────────────────┘

Phase 2:
  ├── LLM Interface & Mock ─────────────────┐
  ├── Prompt Builder ───────────────────────┤
  └── Base Agent ───────────────────────────┘
        │
        └── Deliberation Engine
              │
              └── CLI Runner + Integration Tests

Phase 3:
  ├── Real LLM Integration (Anthropic adapter)
  ├── CLI Demo Runner (rich terminal output)
  └── Prompt Tuning & Threshold Calibration

Phase 4:
  ├── FastAPI Application (REST + SSE)
  └── WebSocket Endpoint (typed events for dashboard)

Phase 5:
  ├── React SPA Setup + WebSocket Hook
  ├── Layout Shell + Control Bar
  ├── Conversation Stream
  ├── Agent Roster
  ├── Energy Chart
  ├── Phase Timeline
  ├── Trigger Log
  ├── Human Intervention + Consensus View
  └── Polish & Responsiveness

Phase 6:
  └── Database Persistence (stretch)

Phase 7:
  ├── Error Handling & Robustness
  ├── Behavioral Tests
  ├── README & Repo Polish
  └── Video Production
```

---

## Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| **Backend** | | |
| Language | Python 3.11+ | Async support, LLM ecosystem |
| Models | Pydantic v2 | Validation, serialization, config |
| API | FastAPI | Async, WebSocket, Pydantic integration |
| Testing | pytest + pytest-asyncio | Standard, fixtures, async support |
| LLM | Anthropic SDK | Primary LLM target |
| Config | PyYAML + Pydantic | YAML validated through Pydantic |
| CLI | rich | Color-coded terminal output |
| **Frontend** | | |
| Framework | React 18+ | Component model, hooks, ecosystem |
| Language | TypeScript | Type safety matching Pydantic models |
| Build | Vite | Fast dev server, simple config |
| Charts | Recharts | React-native charting, real-time friendly |
| Styling | Tailwind CSS | Rapid UI development, dark mode |
| Animations | framer-motion | Smooth transitions for phase changes |

### Dependencies by Phase

**Phase 1-2** (zero external services):
- pydantic, pyyaml
- pytest, pytest-asyncio

**Phase 3** (LLM calls):
- anthropic, rich

**Phase 4** (API):
- fastapi, uvicorn, httpx, websockets

**Phase 5** (web dashboard):
- react, react-dom, typescript, vite
- recharts, tailwindcss, framer-motion

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM output unparseable | Agent produces invalid Post | Structured output with fallback parsing; mock-first dev |
| Energy never terminates | Infinite loop | Hard cap at max_turns; integration tests verify termination |
| Phase oscillation | Confusing agent behavior | Hysteresis with tunable threshold; behavioral tests |
| Trigger rules too noisy | Agents over-respond | Refractory period; phase modulation; integration monitoring |
| Trigger rules too quiet | Agents under-respond | Silence-breaking rule as safety net; min-responders in engine |
| WebSocket reliability | Dashboard misses events | Sequence-based reconnection; event replay from server |
| Dashboard performance | Sluggish with many posts | Virtualized list for conversation stream; throttled chart updates |

---

## What's Explicitly Out of Scope (for now)

- Knowledge service / RAG / pgvector — stub interface, implement later
- Monitoring / Prometheus metrics — add after core works
- Docker / deployment — local development first
- Authentication / multi-tenancy
- Mobile responsive layout (1280px+ only)

---

*Plan created: 2026-02-10*
*Updated: 2026-02-10 (web dashboard added, timeline constraints removed)*
*Colloquip v0.1 — Emergent Deliberation System*
