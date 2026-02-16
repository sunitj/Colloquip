# CLAUDE.md — Colloquip Developer Guide

## Project Overview

Colloquip is an emergent multi-agent deliberation platform. AI agents with distinct personas (biology, chemistry, clinical, regulatory, red-team, etc.) debate hypotheses through self-organizing phases, driven by energy-based dynamics rather than hardcoded turn sequences. The platform is structured as a Reddit-like social system with communities ("subreddits"), persistent agent identities, institutional memory, and event-driven watchers.

**Philosophy**: Inspired by cellular automata — complex behavior emerges from simple rules. Agents self-select when to speak via triggers, an observer detects phases from conversation metrics, and deliberations terminate when energy decays.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Database | SQLAlchemy 2.0+ async ORM, Alembic migrations |
| DB engines | SQLite (dev, via aiosqlite), PostgreSQL 16 + pgvector (prod) |
| LLM | Anthropic Claude (via `anthropic` SDK) |
| Embeddings | OpenAI (optional), mock provider for dev |
| Frontend | React 19, TypeScript 5.9, Vite 7 |
| UI | Radix UI + Tailwind CSS 4 + CVA (shadcn pattern) |
| State | Zustand (client), TanStack React Query (server) |
| Routing | TanStack Router (file-based) |
| Package mgr | uv (Python), npm (frontend) |
| Build system | Hatchling (Python), Vite (frontend) |
| Linting | ruff (Python), ESLint (frontend) |
| Testing | pytest + pytest-asyncio (backend) |
| Containers | Docker multi-stage, docker-compose |
| CI/CD | GitHub Actions |

## Repository Structure

```
Colloquip/
├── src/colloquip/           # Python backend package
│   ├── api/                 # FastAPI app, routes, WebSocket, platform manager
│   ├── agents/              # Agent base class, persona loading, prompts
│   ├── db/                  # SQLAlchemy models (tables.py), engine, repository
│   ├── llm/                 # LLM interface (Anthropic + Mock implementations)
│   ├── memory/              # Institutional memory: store, retriever, extractor
│   ├── embeddings/          # Embedding interface (OpenAI + Mock)
│   ├── watchers/            # Event monitors: literature, scheduled, webhook
│   ├── tools/               # External tools: web search, PubMed, citation verifier
│   ├── feedback/            # Outcome tracking, confidence calibration
│   ├── notifications/       # Notification store
│   ├── eval/                # Prompt evaluation harness
│   ├── engine.py            # EmergentDeliberationEngine (core orchestration)
│   ├── observer.py          # ObserverAgent (phase detection from metrics)
│   ├── energy.py            # EnergyCalculator (termination logic)
│   ├── triggers.py          # TriggerEvaluator (agent activation rules)
│   ├── models.py            # Pydantic domain models
│   ├── config.py            # YAML config loading (energy, observer, trigger params)
│   ├── settings.py          # Environment settings (pydantic-settings)
│   ├── cli.py               # CLI entry point
│   ├── metrics.py           # Prometheus metrics
│   └── cost_tracker.py      # Token/cost tracking
├── web/                     # React frontend (SPA)
│   ├── src/
│   │   ├── components/      # UI components organized by domain
│   │   │   ├── ui/          # Radix + Tailwind primitives (button, card, dialog, etc.)
│   │   │   ├── shared/      # Reusable: AgentAvatar, StanceBadge, PhaseBadge, etc.
│   │   │   ├── layout/      # AppShell, AppSidebar, PageHeader, RightPanel
│   │   │   ├── deliberation/# ConversationFeed, PostCard, EnergyGauge, PhaseTimeline
│   │   │   ├── communities/ # CommunityCard, CommunityHeader, Members/Watchers panels
│   │   │   ├── threads/     # ThreadCard, ThreadHeader, ThreadCostSummary
│   │   │   ├── agents/      # AgentCard, AgentProfileHeader, CalibrationGauge
│   │   │   ├── dialogs/     # Create community/thread/watcher, report outcome
│   │   │   ├── memories/    # MemoryCard, AnnotationForm, AnnotationList
│   │   │   └── notifications/
│   │   ├── routes/          # File-based routes (TanStack Router)
│   │   ├── hooks/           # useWebSocket, useDeliberation, useMediaQuery
│   │   ├── stores/          # Zustand: deliberationStore, themeStore, sidebarStore
│   │   ├── lib/             # api.ts, websocket.ts, query.ts, utils.ts
│   │   └── types/           # deliberation.ts, platform.ts
│   └── package.json
├── tests/                   # pytest test suite (37+ files)
├── alembic/                 # Database migrations (4 migration files)
├── config/                  # YAML configuration files
├── scripts/                 # pre-commit hook, install-hooks.sh, healthcheck.py
├── docs/                    # Design docs (system design, energy model, observer, triggers, prompts)
├── plan/                    # Implementation plans and evolution strategy
├── demo/                    # Playwright demo script for competition video
├── issues/                  # QA reports
├── docker-compose.yml       # Production: app + postgres + redis
├── docker-compose.dev.yml   # Development overrides with hot-reload
├── docker-compose.monitoring.yml  # Prometheus + Grafana
├── Dockerfile               # Multi-stage production build
├── Dockerfile.dev           # Development image with debug support
├── pyproject.toml           # Python project config (hatchling, deps, ruff, pytest)
└── uv.lock                  # Locked Python dependencies
```

## Quick Start (Docker Compose)

The recommended way to run Colloquip is via Docker Compose. A single command brings up the full stack (FastAPI backend + React SPA + PostgreSQL + pgvector + Redis):

```bash
# Production — builds multi-stage image, serves frontend from FastAPI on port 8000
docker compose up -d

# View logs
docker compose logs -f app

# Stop
docker compose down
```

The app is available at `http://localhost:8000`. The React SPA, REST API, and WebSocket all share this single origin — no separate frontend server needed.

### Development with Docker

```bash
# Development — hot-reload (backend), debug port 5678, source volumes mounted
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# With monitoring (Prometheus on :9090, Grafana on :3000)
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
```

The dev override mounts `src/`, `tests/`, `config/`, `web/`, and `alembic/` as volumes so changes are reflected without rebuilding. Uses `EMBEDDING_PROVIDER=mock` and `MEMORY_STORE=in_memory` for fast iteration.

### Docker Compose Services

| Service | Image | Ports | Purpose |
|---------|-------|-------|---------|
| `app` | Custom (multi-stage) | 8000 | FastAPI + static SPA |
| `postgres` | pgvector/pgvector:pg16 | 5432 (dev only) | Database with vector extension |
| `redis` | redis:7-alpine | 6379 (dev only) | Watcher job queue |
| `prometheus` | prom/prometheus (monitoring) | 9090 | Metrics collection |
| `grafana` | grafana/grafana (monitoring) | 3000 | Dashboards |

### Environment Variables for Docker

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Required for live LLM mode:
#   ANTHROPIC_API_KEY=sk-ant-...
# Optional:
#   DB_PASSWORD=colloquip       (default: colloquip)
#   EMBEDDING_PROVIDER=mock     (mock or openai)
#   LOG_LEVEL=INFO
```

Docker Compose reads `.env` automatically. For mock mode (no API keys needed), the defaults work out of the box.

## Quick Reference Commands (without Docker)

For local development without containers:

### Backend

```bash
# Install dependencies
uv sync --group dev

# Run API server (development)
uv run uvicorn colloquip.api:create_app --factory --reload --port 8000

# Run CLI deliberation
uv run colloquip --hypothesis "Your hypothesis here" --mode mock

# Run all fast tests
uv run pytest tests/ -x -m "not slow and not integration"

# Run full test suite including integration
uv run pytest tests/ -x

# Run tests with coverage
uv run pytest tests/ --cov=colloquip --cov-report=term-missing

# Lint
uv run ruff check .

# Format check
uv run ruff format --check .

# Auto-fix lint + format
uv run ruff check --fix . && uv run ruff format .

# Run Alembic migrations
uv run alembic upgrade head
```

### Frontend

```bash
cd web

# Install dependencies
npm install

# Dev server (proxies API to localhost:8000)
npm run dev

# Production build (runs tsc then vite build)
npm run build

# Lint
npm run lint
```

## Architecture & Key Concepts

### Core Deliberation Loop

1. **Session created** with a hypothesis and agent configs
2. **Seed phase**: All agents produce initial posts
3. **Main loop** (each turn):
   - ObserverAgent calculates conversation metrics → detects phase
   - EnergyCalculator computes energy score
   - TriggerEvaluator selects which agents should respond
   - Selected agents generate posts via LLM
   - Events broadcast to WebSocket subscribers
4. **Termination**: Energy < 0.2 for 3 consecutive turns, or max posts reached
5. **Synthesis**: ConsensusMap generated (agreements, disagreements, minority positions)

### Phases

`EXPLORE → DEBATE → DEEPEN → CONVERGE → SYNTHESIS`

Phases are **detected by the observer from metrics**, not sequenced. The system can oscillate between phases based on conversation dynamics.

### Energy Model

```
E = 0.4×novelty + 0.3×disagreement + 0.2×questions - 0.1×staleness
```

Energy decays naturally as the conversation converges. New knowledge, red-team challenges, or human intervention can inject energy.

### Agents

Each agent has: persona prompt, phase mandates, domain keywords, knowledge scope, and an optional red-team flag. Agents self-select via triggers (relevance, silence-breaking, bridge, red-team). All subreddits must have at least one red-team agent.

### Platform Model

- **Subreddits** (communities): Domain-scoped deliberation spaces
- **AgentIdentities**: Persistent agents with expertise, recruited into subreddits
- **Threads**: Individual deliberation sessions within a subreddit
- **Institutional Memory**: Bayesian-confidence synthesis memories with temporal decay
- **Watchers**: Literature monitors, scheduled triggers, webhooks that auto-spawn deliberations

## Database & Migrations

- **Development**: SQLite via aiosqlite (no setup needed)
- **Production**: PostgreSQL 16 + pgvector extension

Four Alembic migration files:
1. `001_baseline_schema.py` — Core + platform tables
2. `002_phase3_memory_tables.py` — Synthesis memory
3. `003_phase4_watcher_tables.py` — Event watchers
4. `004_phase5_crossref_outcome_tables.py` — Cross-references & outcomes

Key tables: `deliberation_sessions`, `posts`, `energy_history`, `consensus_maps`, `subreddits`, `agent_identities`, `subreddit_memberships`, `syntheses`, `synthesis_memories`, `watchers`, `watcher_events`, `notifications`, `cross_references`, `outcome_reports`, `memory_annotations`, `cost_records`.

## API Endpoints

All REST endpoints are prefixed with `/api/`:

| Group | Key Endpoints |
|-------|-------------|
| Deliberations | `POST /deliberations`, `POST /deliberations/{id}/start` (SSE), `GET /deliberations/{id}`, `GET /deliberations/{id}/posts` |
| Platform | `POST /subreddits`, `GET /subreddits`, `POST /subreddits/{id}/threads`, `GET /agents` |
| Memory | `GET /memories/search`, `POST /memories/{id}/annotations` |
| Watchers | `POST /watchers`, `POST /watchers/{id}/trigger`, `GET /notifications` |
| Export | `POST /deliberations/{id}/export/markdown`, `POST /deliberations/{id}/export/pdf` |
| Feedback | `POST /outcomes`, `GET /outcomes/{session_id}` |
| WebSocket | `WS /ws/sessions/{session_id}` |
| Health | `GET /health` |

## Testing Conventions

- **Framework**: pytest with `asyncio_mode = "auto"`
- **Markers**: `@pytest.mark.slow` (real LLM calls), `@pytest.mark.integration` (full loops)
- **Mocking**: MockLLM and MockEmbedding providers for fast tests
- **Fixtures**: Shared factories in `tests/conftest.py` — `create_post()`, `create_session()`, `create_agent_config()`, `create_metrics()`
- **Coverage target**: 80%+
- **Pre-commit hook**: Runs `ruff check`, `ruff format --check`, and fast unit tests

Run fast tests before committing:
```bash
uv run pytest tests/ -x -q -m "not slow and not integration"
```

## Code Style & Conventions

### Python

- **Line length**: 100 characters (configured in ruff)
- **Target version**: Python 3.11+
- **Linter rules**: E (pycodestyle errors), F (pyflakes), I (isort)
- **Ignored**: E402 (module-level imports after `load_dotenv()` are intentional)
- **Async throughout**: All DB operations, LLM calls, and API handlers are async
- **Type hints**: Pydantic models for data, type annotations on functions
- **Repository pattern**: `SessionRepository` abstracts all DB access
- **Interface pattern**: Abstract base classes for LLM, Embedding, Tool, and Watcher

### TypeScript / React

- **Strict mode** with strict null checks
- **Path alias**: `@/` maps to `web/src/`
- **Component pattern**: Radix primitive → Tailwind + CVA wrapper → domain component
- **State**: Zustand for client state (with persist middleware), TanStack Query for server state
- **Styling**: Tailwind CSS utility classes, CSS custom properties for theming
- **Class merging**: `cn()` utility (clsx + tailwind-merge)
- **Three themes**: dark (default), light, pastel — all via CSS variables in `app.css`
- **Route file**: `web/src/routeTree.gen.ts` is auto-generated — do not edit manually

### File Organization

- Group components by domain (deliberation, communities, threads, agents, memories)
- Shared/reusable components go in `components/shared/` or `components/ui/`
- API functions centralized in `web/src/lib/api.ts`
- Query keys in `web/src/lib/queryKeys.ts`
- TypeScript types in `web/src/types/`

## CI/CD Pipeline

GitHub Actions workflows in `.github/workflows/`:

1. **ci.yml** (push to main/claude/*, PRs to main):
   - `lint`: ruff check + format check
   - `test-unit`: pytest (Python 3.11, 3.12 matrix) with coverage
   - `test-integration`: Full loop tests (depends on unit passing)

2. **deploy.yml** (tags matching `v*`):
   - Run full test suite → build Docker image → push to GHCR

3. **db-migration.yml** (PRs touching db/alembic files):
   - Validates migrations apply cleanly

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///colloquip.db` | Database connection string |
| `ANTHROPIC_API_KEY` | — | Required for real LLM mode |
| `OPENAI_API_KEY` | — | Required for OpenAI embeddings |
| `ENVIRONMENT` | `development` | `development` or `production` |
| `EMBEDDING_PROVIDER` | `mock` | `mock` or `openai` |
| `MEMORY_STORE` | `in_memory` | `in_memory` or `pgvector` |
| `LOG_LEVEL` | `DEBUG` | Standard Python log levels |
| `LOG_FORMAT` | `text` | `text` or `json` |
| `WATCHER_POLL_INTERVAL` | `300` | Seconds between watcher polls |

## Common Development Tasks

### Adding a new API endpoint

1. Add route handler in the appropriate `src/colloquip/api/*_routes.py` file
2. Register the router in `src/colloquip/api/__init__.py` if it's a new router
3. Add corresponding API function in `web/src/lib/api.ts`
4. Add tests in `tests/`

### Adding a new database table

1. Define the SQLAlchemy model in `src/colloquip/db/tables.py`
2. Create an Alembic migration: `uv run alembic revision --autogenerate -m "description"`
3. Add repository methods in `src/colloquip/db/repository.py`
4. Add Pydantic model in `src/colloquip/models.py` if needed

### Adding a new agent persona

1. Agent configs are defined in `src/colloquip/agents/` with persona prompts
2. Each agent needs: `agent_id`, `display_name`, `persona_prompt`, `phase_mandates`, `domain_keywords`, `knowledge_scope`
3. Register in the agent pool / persona loader

### Adding a new watcher type

1. Implement `BaseWatcher` interface in `src/colloquip/watchers/`
2. Register in `WatcherManager`
3. Add corresponding DB model if needed
4. Add API routes in `watcher_routes.py`

## Important Design Decisions

- **No hardcoded phase sequences**: Phases are emergent from conversation metrics
- **Trigger-based agent selection**: Agents don't take fixed turns; they activate when triggered
- **Energy as termination signal**: Deliberations end when productive energy decays, not after N turns
- **Bayesian memory confidence**: Memories use Beta distributions with temporal decay (120-day half-life)
- **Mock-first development**: All external services (LLM, embeddings) have mock implementations for testing
- **Repository pattern**: All DB access goes through `SessionRepository` — never query tables directly in routes
- **Frontend served by backend**: Production builds the React SPA into static files served by FastAPI
