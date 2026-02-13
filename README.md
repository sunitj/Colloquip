# Colloquip

**Emergent multi-agent deliberation — where serendipity arises from simple rules, not engineered detection.**

Colloquip is an emergent multi-agent deliberation system inspired by cellular automata: simple local rules produce complex global behavior. Six specialist agents debate scientific hypotheses without a fixed schedule or hardcoded turns. Instead, agents decide *when* to speak based on trigger rules, an Observer detects *what phase* the conversation is in, and an energy model determines *when* to stop.

## What Makes This Different

| Traditional Multi-Agent | Colloquip (Emergent) |
|---|---|
| Fixed turn order (Agent A, then B, then C...) | Agents self-select when to speak via trigger rules |
| Predefined phase schedule | Observer detects phases from conversation dynamics |
| Hard turn limit or human stop | Energy-based termination (conversation dies naturally) |
| Orchestrator decides who speaks | No orchestrator — emergence from simple rules |

## Architecture

```
                    ┌─────────────────────────┐
                    │     Observer Agent       │
                    │  (phase detection with   │
                    │   hysteresis)            │
                    └────────────┬────────────┘
                                 │ PhaseSignal
    ┌────────────────────────────┼────────────────────────────┐
    │                            │                            │
    ▼                            ▼                            ▼
┌────────┐  ┌────────┐  ┌────────────┐  ┌────────┐  ┌────────┐  ┌──────────┐
│Biology │  │Chem    │  │  ADMET     │  │Clinical│  │Regulat.│  │Red Team  │
│Agent   │  │Agent   │  │  Agent     │  │Agent   │  │Agent   │  │Agent     │
└───┬────┘  └───┬────┘  └─────┬──────┘  └───┬────┘  └───┬────┘  └────┬─────┘
    │           │             │              │           │             │
    │  Trigger  │  Trigger    │   Trigger    │  Trigger  │  Trigger    │ Trigger
    │  Rules    │  Rules      │   Rules      │  Rules    │  Rules      │ Rules
    └─────┬─────┴──────┬──────┴──────┬───────┴─────┬─────┴──────┬─────┘
          │            │             │             │            │
          ▼            ▼             ▼             ▼            ▼
    ┌───────────────────────────────────────────────────────────────┐
    │                 Energy Calculator                              │
    │  E = w_n·novelty + w_d·disagreement + w_q·questions           │
    │      - w_s·staleness                                          │
    │  Terminate when E < threshold for 3 consecutive turns         │
    └───────────────────────────────────────────────────────────────┘
```

## Key Technical Highlights

- **9 Trigger Rules**: relevance, disagreement, question, silence-breaking, bridge opportunity, uncertainty response, + 3 Red Team rules (consensus-forming, criticism-gap, premature-convergence)
- **Hysteresis Phase Detection**: Prevents oscillation — requires 3 consecutive signals before transitioning between EXPLORE, DEBATE, DEEPEN, CONVERGE, SYNTHESIS
- **Energy-Based Termination**: Normalized energy formula with 4 components (novelty, disagreement, questions, staleness). Conversation ends when ideas run dry, not when a timer expires
- **Red Team Agent**: Automatically challenges consensus — fires when 3+ agents agree without criticism
- **Human Intervention**: Inject questions/data mid-deliberation; boosts energy to extend the conversation
- **Real-Time Web UI**: Dark-first React SPA with WebSocket streaming — social feed deliberation view, community management, agent profiles, and live energy/phase visualization

## Quick Start

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Node.js 18+ (for web dashboard)

### Install & Run

```bash
# Clone and install
git clone https://github.com/sunitj/Colloquip.git
cd Colloquip
uv sync --group dev --all-extras

# Run with mock LLM (no API key needed)
uv run colloquip --mode mock "GLP-1 agonists improve cognitive function in Alzheimer's patients"

# Run with real Claude API
export ANTHROPIC_API_KEY=your-key-here
uv run colloquip --mode real "GLP-1 agonists improve cognitive function in Alzheimer's patients"

# Save transcript
uv run colloquip --mode mock --save-transcript output.json "Your hypothesis here"
```

### API Server

```bash
# Start the FastAPI server
uv run uvicorn colloquip.api:create_app --factory --reload

# With database persistence
DATABASE_URL=sqlite+aiosqlite:///colloquip.db uv run uvicorn colloquip.api:create_app --factory --reload
```

### Web Dashboard

```bash
cd web
npm install
npm run dev
# Open http://localhost:5173
```

### Run Tests

```bash
uv run pytest                    # All 181 tests
uv run pytest -m integration     # Integration tests only
uv run pytest tests/test_behavioral.py  # Emergent behavior tests
```

## Project Structure

```
colloquip/
├── src/colloquip/
│   ├── models.py          # Pydantic data models (Post, Phase, Energy, etc.)
│   ├── config.py          # Configuration with YAML loading
│   ├── energy.py          # Energy calculator + termination logic
│   ├── observer.py        # Observer agent (rule-based phase detection)
│   ├── triggers.py        # Trigger evaluator (agent self-selection)
│   ├── engine.py          # Main emergent deliberation loop
│   ├── agents/            # Agent framework + prompt builder
│   ├── llm/               # LLM interface, mock, Anthropic adapter
│   ├── api/               # FastAPI REST + SSE + WebSocket
│   ├── db/                # SQLAlchemy async persistence
│   ├── cli.py             # CLI runner
│   └── display.py         # Rich terminal output
├── web/                   # React 19 + TypeScript frontend (dark-first, shadcn/ui)
│   └── src/
│       ├── components/    # ui/ (shadcn), layout/, shared/, deliberation/, dialogs/
│       ├── routes/        # TanStack Router file-based pages
│       ├── hooks/         # useDeliberation, useMediaQuery
│       ├── stores/        # Zustand (deliberation state, sidebar state)
│       ├── lib/           # API client, WebSocket, query config, utilities
│       └── types/         # TypeScript types (deliberation, platform)
├── tests/                 # 181 tests (unit + integration + behavioral)
├── config/                # YAML configs for agents and engine
└── plan/                  # Implementation plan and design docs
```

## How It Works

1. **Seed Phase**: All 6 agents produce initial posts about the hypothesis
2. **Emergent Loop** (repeats until energy depletes):
   - Observer calculates conversation metrics and detects the current phase
   - Energy calculator checks if conversation should terminate
   - Each agent's trigger evaluator decides if it should respond
   - Responding agents generate posts concurrently
   - Energy is updated based on novelty, disagreement, questions, staleness
3. **Synthesis**: LLM generates a ConsensusMap with agreements, disagreements, minority positions, and serendipitous connections

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/deliberations` | Create a new deliberation session |
| `POST` | `/api/deliberations/{id}/start` | Start deliberation (SSE stream) |
| `POST` | `/api/deliberations/{id}/intervene` | Human intervention |
| `GET` | `/api/deliberations/{id}` | Get session state |
| `GET` | `/api/deliberations/{id}/energy` | Energy history |
| `GET` | `/api/deliberations` | List all sessions |
| `WS` | `/ws/deliberations/{id}` | Real-time WebSocket stream |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy (async), Pydantic v2 |
| LLM | Anthropic Claude (via SDK), Mock LLM for testing |
| Frontend | React 19, TypeScript, Vite 7, Tailwind CSS v4 |
| UI Components | shadcn/ui pattern (Radix UI + Tailwind + cva) |
| State | TanStack Query (server), Zustand (client), TanStack Router (routing) |
| Animation | Framer Motion |
| Testing | pytest, pytest-asyncio (181 tests) |
| Package Manager | uv (reproducible builds via lockfile) |

## Documentation

| Document | Description |
|----------|-------------|
| [Frontend Redesign Plan](plan/FRONTEND_REBUILD_PLAN.md) | Complete frontend overhaul — dark-first, shadcn/ui, social feed UX |
| [Implementation Plan](plan/IMPLEMENTATION_PLAN.md) | Phased build plan with success criteria |
| [Social Platform Plan](plan/SOCIAL_PLATFORM_PLAN.md) | Reddit-like social platform architecture |
| [Evolution Plan](plan/EVOLUTION_PLAN.md) | Backend evolution from engine to platform |
| [System Design](docs/SYSTEM_DESIGN.md) | Architecture, data models, API, data flow |
| [Energy Model](docs/ENERGY_MODEL.md) | Energy calculation and termination logic |
| [Observer Spec](docs/OBSERVER_SPEC.md) | Phase detection, hysteresis, meta-observations |
| [Agent Prompts](docs/AGENT_PROMPTS.md) | All agent personas and phase mandates |
| [Trigger Rules](docs/TRIGGER_RULES.md) | Agent self-selection trigger rules |
