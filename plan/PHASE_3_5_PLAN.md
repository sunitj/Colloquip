# Phase 3-5 Implementation Plan

## Context

**Starting point:** Phase 1-2 is complete — 313 tests passing, 10 curated personas,
subreddit system, tool integrations (PubMed, company docs, web search), template-driven
synthesis with audit chains, cost tracking, citation verification, human participation
models, FastAPI + WebSocket API, React dashboard, SQLite persistence.

**This plan covers:** Institutional Memory (Phase 3), Event-Driven Triggers (Phase 4),
Cross-Subreddit References & Feedback Loops (Phase 5), and the **Deployment Infrastructure**
needed to run Phase 3-5 in production.

**Source spec:** `docs/IMPLEMENTATION_PROMPT_PHASE_3_5.md`

---

## Guiding Principles (Unchanged)

1. **Make it work -> Make it right -> Make it fast** — Mock embeddings first, pgvector later
2. **Testable in isolation** — Every retriever, watcher, triage agent testable without LLM/DB
3. **Interfaces first** — `EmbeddingProvider` protocol before any OpenAI implementation
4. **Configuration-driven** — Retrieval limits, decay rates, triage thresholds all in config
5. **Minimal dependencies** — pgvector/asyncpg only added when actually needed (Sprint 11)

---

## Current Architecture Gaps

| Gap | Phase Impact | Resolution |
|-----|-------------|------------|
| No embedding infrastructure | Phase 3 blocked | Add `EmbeddingProvider` interface + mock + OpenAI impl |
| SQLite-only DB in dev | No vector search | Add PostgreSQL + pgvector support |
| No background task scheduler | Phase 4 blocked | Add async polling framework for watchers |
| No notification system | Phase 4 blocked | Build notification store + WebSocket events + API |
| Synthesis not persisted as memory | Phase 3 blocked | Add post-deliberation memory storage pipeline |
| No containerization | Deployment blocked | Add Dockerfile, docker-compose, health checks |
| No CI/CD | Quality at risk | Add GitHub Actions for tests, lint, build |
| No DB migrations | Schema evolution blocked | Add Alembic migration framework |
| No secrets management | Production blocked | Add environment-based config with validation |

---

## Sprint Plan

### Sprint 8: Embedding Interface + In-Memory Vector Store

**Goal:** Define the embedding abstraction and a testable in-memory implementation.

**New files:**

| File | Purpose |
|------|---------|
| `src/colloquip/embeddings/__init__.py` | Package init |
| `src/colloquip/embeddings/interface.py` | `EmbeddingProvider` ABC: `embed(text)`, `embed_batch(texts)`, configurable `dimension` |
| `src/colloquip/embeddings/mock.py` | `MockEmbeddingProvider` — deterministic hash-based embeddings. Same text = same vector. `cosine_similarity()` utility |
| `src/colloquip/memory/__init__.py` | Package init |
| `src/colloquip/memory/store.py` | `SynthesisMemory` model, `MemoryStore` ABC (`save`, `search`, `search_global`), `InMemoryStore` (brute-force cosine) |
| `src/colloquip/memory/retriever.py` | `MemoryRetriever` class, `RetrievedMemories` model with `format_for_prompt()` |
| `tests/test_embeddings.py` | Mock determinism, cosine similarity, batch embedding |
| `tests/test_memory.py` | Store save/search/ranking, retriever arena vs global scoping, format output |

**Modified files:** None.

**Tests:** ~20 new. **Gate:** Store synthesis memories and retrieve top-k similar ones in-memory.

---

### Sprint 9: Synthesis -> Memory Pipeline

**Goal:** After a deliberation completes, automatically extract and store a memory.

**New files:**

| File | Purpose |
|------|---------|
| `src/colloquip/memory/extractor.py` | `SynthesisMemoryExtractor`: extracts `key_conclusions` from synthesis sections, `citations_used` from `[PUBMED:xxx]` refs, `agents_involved` from audit chains, generates embedding. Pure text parsing — no LLM calls |

**Modified files:**

| File | Change |
|------|--------|
| `src/colloquip/api/platform_manager.py` | Add `memory_store` + `embedding_provider` to init. Add `store_synthesis_memory()`. Wire into thread completion |
| `src/colloquip/engine.py` | After synthesis, call memory storage pipeline. Broadcast `memory_stored` event |
| `src/colloquip/api/ws.py` | Add `memory_stored` event type |

**Tests:** ~15 new. **Gate:** Completing a deliberation automatically creates a searchable memory.

---

### Sprint 10: Prompt Integration (RAG Layer)

**Goal:** Inject retrieved memories into agent prompts for new deliberations.

**Modified files:**

| File | Change |
|------|--------|
| `src/colloquip/agents/prompts.py` | Add `build_memory_context(memories)` helper. Add optional `prior_deliberations` parameter to `build_v3_system_prompt()`. Include instructions: reference prior conclusions, flag contradictions, don't repeat, check for new evidence |
| `src/colloquip/engine.py` | Before deliberation starts, call `memory_retriever.retrieve()`. Pass retrieved memories to prompt builder. Broadcast `memories_retrieved` event |
| `src/colloquip/api/ws.py` | Add `memories_retrieved` event type |

**Tests:** ~10 new. **Gate:** 5th deliberation on a related topic references conclusions from earlier ones.

---

### Sprint 11: PostgreSQL + pgvector + Alembic

**Goal:** Production-grade persistence with vector search. Add migration framework.

**New files:**

| File | Purpose |
|------|---------|
| `src/colloquip/embeddings/openai.py` | `OpenAIEmbeddingProvider` — calls `text-embedding-3-small`. Rate limiting, retry. Falls back to mock if no API key |
| `src/colloquip/memory/pgvector_store.py` | `PgVectorMemoryStore(MemoryStore)` — pgvector cosine similarity search, IVFFlat index |
| `alembic.ini` | Alembic configuration |
| `alembic/env.py` | Migration environment (async support) |
| `alembic/versions/001_initial_schema.py` | All existing tables as baseline migration |
| `alembic/versions/002_synthesis_memories.py` | `synthesis_memories` + `memory_annotations` tables with `vector(1536)` columns |

**Modified files:**

| File | Change |
|------|--------|
| `src/colloquip/db/tables.py` | Add `DBSynthesisMemory`, `DBMemoryAnnotation` table models |
| `src/colloquip/db/repository.py` | Add `save_memory()`, `search_memories()`, `get_memory()`, `save_annotation()`, `get_annotations()` |
| `src/colloquip/config.py` | Add `EMBEDDING_PROVIDER=mock|openai`, `MEMORY_STORE=in_memory|pgvector` config |
| `pyproject.toml` | Add `pgvector` optional dependency group: `asyncpg`, `pgvector`, `openai`, `alembic` |

**Tests:** ~15 new. **Gate:** Memories persist across restarts. Search works with real embeddings.

---

### Sprint 12: Human Memory Corrections

**Goal:** Let humans annotate/correct stored memories.

**New files:**

| File | Purpose |
|------|---------|
| `src/colloquip/api/memory_routes.py` | `GET /api/memories`, `GET /api/memories/{id}`, `POST /api/memories/{id}/annotate`, `GET /api/subreddits/{name}/memories` |

**Modified files:**

| File | Change |
|------|--------|
| `src/colloquip/models.py` | Add `MemoryAnnotationType` enum (OUTDATED, CORRECTION, CONFIRMED, CONTEXT), `MemoryAnnotation` model |
| `src/colloquip/memory/store.py` | Add `annotate()`, `get_with_annotations()` to `MemoryStore` interface |
| `src/colloquip/memory/retriever.py` | Include annotations in prompt formatting: `[Human correction: ...]` |
| `src/colloquip/api/app.py` | Mount memory routes |

**Tests:** ~12 new. **Gate:** Human marks memory as outdated; next deliberation sees the correction.

---

### Sprint 13: Phase 3 Validation + Phase 3b Prep

**Goal:** Validate Phase 3a meets all criteria. Define typed memory models for future use.

**Validation (from spec):**
1. Run 5 deliberations on related topics in same subreddit
2. 5th deliberation's posts reference conclusions from earlier ones
3. Synthesis builds on (doesn't repeat) prior conclusions
4. Memory annotations propagate correctly

**Phase 3b prep (models only, not implemented):**

| File | Change |
|------|--------|
| `src/colloquip/models.py` | Add `MemoryType` enum (FACTUAL, METHODOLOGICAL, POSITIONAL, RELATIONAL, CONTEXTUAL), `MemoryScope` enum (GLOBAL, ARENA), `TypedMemory` model |
| `alembic/versions/003_typed_memories.py` | `typed_memories` table (reserved, not populated) |

**Tests:** ~8 new. **Gate:** Phase 3a validated. Phase 3b models defined.

---

### Sprint 14: Watcher Models + Triage Agent

**Goal:** Define watcher/event/triage models and implement triage evaluation.

**New files:**

| File | Purpose |
|------|---------|
| `src/colloquip/watchers/__init__.py` | Package init |
| `src/colloquip/watchers/interface.py` | `BaseWatcher` ABC: `poll() -> List[WatcherEvent]`. `WatcherManager`: registers watchers, runs poll loop. Rate limiting, error handling |
| `src/colloquip/watchers/triage.py` | `TriageAgent`: single LLM call, <500 tokens, evaluates NOVELTY/RELEVANCE/SIGNAL/URGENCY. Returns `TriageDecision` (low/medium/high). `MockTriageAgent` for testing |
| `tests/test_watchers.py` | Triage decisions, signal classification, deduplication |

**Modified files:**

| File | Change |
|------|--------|
| `src/colloquip/models.py` | Add `WatcherType`, `WatcherConfig`, `WatcherEvent`, `WatcherSource`, `TriageDecision`, `TriageSignal` models |

**Tests:** ~15 new. **Gate:** Triage agent evaluates mock events and produces signal decisions.

---

### Sprint 15: Watcher Implementations

**Goal:** Implement concrete watchers (literature, scheduled, webhook).

**New files:**

| File | Purpose |
|------|---------|
| `src/colloquip/watchers/literature.py` | `LiteratureWatcher(BaseWatcher)` — reuses `PubMedTool._esearch()`. Tracks `last_checked`, returns only new papers |
| `src/colloquip/watchers/scheduled.py` | `ScheduledWatcher(BaseWatcher)` — fires on cron-like schedule. Config: `interval_days`, `day_of_week`, `time_of_day` |
| `src/colloquip/watchers/webhook.py` | `WebhookWatcher` — `POST /api/webhooks/{watcher_id}` endpoint. Payload validation |
| `src/colloquip/watchers/manager.py` | `WatcherManager` — orchestrates all watchers. Async polling loop. Error isolation per watcher. Event -> Triage -> Notification pipeline |

**Tests:** ~18 new. **Gate:** Literature watcher detects mock papers. Scheduled watcher fires on time.

---

### Sprint 16: Notification System + API

**Goal:** Notify humans of watcher events, let them act on notifications.

**New files:**

| File | Purpose |
|------|---------|
| `src/colloquip/notifications/__init__.py` | Package init |
| `src/colloquip/notifications/store.py` | `Notification` model, `NotificationStore` ABC with in-memory and DB implementations, `NotificationManager` |
| `src/colloquip/api/watcher_routes.py` | `POST /api/subreddits/{name}/watchers`, `GET /api/subreddits/{name}/watchers`, `PUT/DELETE /api/watchers/{id}`, `GET /api/notifications`, `POST /api/notifications/{id}/act` |

**Modified files:**

| File | Change |
|------|--------|
| `src/colloquip/db/tables.py` | Add `DBWatcher`, `DBWatcherEvent`, `DBNotification` tables |
| `src/colloquip/db/repository.py` | Add watcher and notification CRUD |
| `src/colloquip/api/app.py` | Mount watcher routes. Start WatcherManager as background task |
| `src/colloquip/api/ws.py` | Add `notification` event type for real-time notification delivery |
| `alembic/versions/004_watchers_notifications.py` | Migration for watcher/event/notification tables |

**Tests:** ~15 new. **Gate:** Human receives notification, clicks "Create Thread", deliberation starts.

---

### Sprint 17: Auto-Deliberation + Phase 4 Validation

**Goal:** Implement earned auto-deliberation. Validate Phase 4.

**New files:**

| File | Purpose |
|------|---------|
| `src/colloquip/watchers/auto_deliberation.py` | `AutoDeliberationPolicy`: requires 20+ events, >70% useful output, human explicit approval. Rate limit: max 5 auto-threads/hour/watcher. Budget: shares subreddit's monthly budget. Auto-threads tagged for human review |

**Modified files:**

| File | Change |
|------|--------|
| `src/colloquip/watchers/manager.py` | After triage, check auto-deliberation policy. Log all decisions for audit trail |
| `src/colloquip/db/tables.py` | Add `auto_create_thread`, `auto_thread_approval_rate` to `DBWatcher` |

**Phase 4 Validation:**
1. Literature watcher detects new PubMed papers matching configured query
2. Triage summaries rated "helpful" (>80% in mock evaluation)
3. Human creates thread from notification with one action
4. Scheduled watcher fires on time
5. Webhook receives and processes external events
6. Auto-deliberation respects rate limits and budget

**Tests:** ~10 new. **Gate:** Full watcher -> triage -> notify -> act pipeline works end-to-end.

---

### Sprint 18: Cross-Subreddit References

**Goal:** Detect when findings in one subreddit are relevant to another.

**New files:**

| File | Purpose |
|------|---------|
| `src/colloquip/memory/cross_references.py` | `CrossReferenceDetector`: ALL criteria must be met — embedding similarity > 0.75, shared entity (gene/compound/disease/citation), actionable in target context. `CrossReference` model. Entity extraction: regex for PMIDs, gene names, compound IDs |
| `src/colloquip/memory/differ.py` | `DeliberationDiffer`: `diff(earlier, later) -> DeliberationDiff`. Produces new_evidence, changed_conclusions, resolved_disagreements, persistent_uncertainties, overall_trajectory. Uses LLM (with mock) |

**Modified files:**

| File | Change |
|------|--------|
| `src/colloquip/api/memory_routes.py` | Add `GET /api/cross-references`, `POST /api/cross-references/{id}/review`, `GET /api/threads/{id}/diff/{other_id}` |
| `src/colloquip/db/tables.py` | Add `DBCrossReference` table |
| `alembic/versions/005_cross_references.py` | Migration for cross_references table |

**Tests:** ~12 new. **Gate:** Cross-references detected with >70% precision on test data.

---

### Sprint 19: Outcome Tracking + Agent Calibration

**Goal:** Track real-world outcomes and calibrate agent accuracy.

**New files:**

| File | Purpose |
|------|---------|
| `src/colloquip/feedback/__init__.py` | Package init |
| `src/colloquip/feedback/outcome.py` | `OutcomeReport` model, `OutcomeTracker` class |
| `src/colloquip/feedback/calibration.py` | `AgentCalibration`: `compute_calibration(agent_id) -> CalibrationReport`. Metrics: overall accuracy, calibration curve, domain-specific accuracy, systematic biases. Meaningful only after 10+ outcomes |
| `src/colloquip/api/feedback_routes.py` | `POST /api/threads/{id}/outcome`, `GET /api/agents/{id}/calibration`, `GET /api/calibration/overview` |

**Modified files:**

| File | Change |
|------|--------|
| `src/colloquip/db/tables.py` | Add `DBOutcomeReport`, `DBAgentCalibration` tables |
| `src/colloquip/api/app.py` | Mount feedback routes |
| `alembic/versions/006_outcome_calibration.py` | Migration for outcome/calibration tables |

**Tests:** ~12 new. **Gate:** 10 outcomes reported, calibration surfaces agent-specific insights.

---

### Sprint 20: Export + External API + Phase 5 Validation

**Goal:** Export synthesis, allow external submission, validate Phase 5.

**New files:**

| File | Purpose |
|------|---------|
| `src/colloquip/api/export_routes.py` | `GET /api/threads/{id}/export/markdown`, `GET /api/threads/{id}/export/json`, `GET /api/threads/{id}/export/pdf` |
| `src/colloquip/api/external_routes.py` | `POST /api/external/submit` (programmatic hypothesis submission), `GET /api/external/results/{thread_id}` (poll for results). API key authentication |

**Modified files:**

| File | Change |
|------|--------|
| `src/colloquip/api/app.py` | Mount export and external routes |
| `pyproject.toml` | Add `weasyprint` to optional `export` dependency group |

**Phase 5 Validation:**
1. Cross-references detected between related subreddits (precision >70%)
2. Deliberation diff identifies changes between related syntheses
3. 10+ outcomes produce a calibration report
4. Export produces valid markdown, JSON, PDF
5. External API allows submit + poll workflow

**Tests:** ~10 new. **Gate:** Full platform loop works end-to-end.

---

## Deployment Infrastructure

### Sprint D1: Containerization (Parallel with Sprint 8)

**Goal:** Dockerize the application and all dependencies.

**New files:**

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage build: (1) Python deps with uv, (2) Node build for web dashboard, (3) Production image with FastAPI + static files. Based on `python:3.11-slim`. Non-root user. Health check endpoint |
| `Dockerfile.dev` | Development image with hot-reload, dev tools, all optional deps |
| `docker-compose.yml` | Services: `app` (Colloquip), `postgres` (PostgreSQL 16 + pgvector), `redis` (for watcher job queue, Phase 4). Volumes for data persistence. Network isolation |
| `docker-compose.dev.yml` | Override for development: source mounting, debug ports, live reload |
| `.dockerignore` | Exclude `.git`, `__pycache__`, `node_modules`, `.env`, test artifacts |

**Dockerfile structure:**

```dockerfile
# Stage 1: Python dependencies
FROM python:3.11-slim AS python-deps
# Install uv, copy pyproject.toml + uv.lock, install deps

# Stage 2: Frontend build
FROM node:20-slim AS frontend-build
# Copy web/, npm install, npm run build

# Stage 3: Production image
FROM python:3.11-slim AS production
# Copy deps from stage 1, static build from stage 2
# Non-root user, health check, EXPOSE 8000
```

**docker-compose.yml structure:**

```yaml
services:
  app:
    build: .
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: postgresql+asyncpg://colloquip:${DB_PASSWORD}@postgres:5432/colloquip
      EMBEDDING_PROVIDER: openai
      MEMORY_STORE: pgvector
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    depends_on:
      postgres: { condition: service_healthy }
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: pgvector/pgvector:pg16
    volumes: ["pgdata:/var/lib/postgresql/data"]
    environment:
      POSTGRES_DB: colloquip
      POSTGRES_USER: colloquip
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U colloquip"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes: ["redisdata:/data"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]

volumes:
  pgdata:
  redisdata:
```

**Modified files:**

| File | Change |
|------|--------|
| `src/colloquip/api/routes.py` | Add `GET /health` endpoint (DB connectivity, service status) |
| `src/colloquip/config.py` | Add `DatabaseConfig`, `DeploymentConfig` with env var validation. `ENVIRONMENT=development|staging|production` |

---

### Sprint D2: CI/CD Pipeline (Parallel with Sprint 9)

**Goal:** Automated testing, linting, and container builds on every push.

**New files:**

| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | **Test + Lint pipeline**: triggered on push/PR to `main` and feature branches. Jobs: (1) `lint` — ruff check + ruff format --check, (2) `test-unit` — pytest (exclude integration/slow markers), (3) `test-integration` — pytest -m integration with SQLite, (4) `build` — verify Docker image builds. Matrix: Python 3.11, 3.12 |
| `.github/workflows/deploy.yml` | **Deploy pipeline** (triggered on tag push `v*`): (1) Run full test suite, (2) Build + push Docker image to GHCR, (3) Deploy to target environment (configurable) |
| `.github/workflows/db-migration.yml` | **Migration check**: On PR, verify Alembic migrations are valid: `alembic check` + `alembic upgrade head` against empty SQLite |

**CI job details:**

```yaml
# ci.yml
name: CI
on:
  push:
    branches: [main, claude/*]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --group dev
      - run: uv run ruff check .
      - run: uv run ruff format --check .

  test-unit:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with: { python-version: "${{ matrix.python-version }}" }
      - run: uv sync --group dev
      - run: uv run pytest -x --ignore=tests/test_integration_e2e.py -m "not slow and not integration" --cov=colloquip --cov-report=xml
      - uses: codecov/codecov-action@v4  # optional

  test-integration:
    runs-on: ubuntu-latest
    needs: test-unit
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --group dev
      - run: uv run pytest -m integration

  build:
    runs-on: ubuntu-latest
    needs: [lint, test-unit]
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t colloquip:ci .
```

---

### Sprint D3: Production Configuration (Parallel with Sprint 11)

**Goal:** Environment-based configuration, secrets management, logging.

**New files:**

| File | Purpose |
|------|---------|
| `.env.example` | Template with all required/optional env vars, documented |
| `src/colloquip/logging_config.py` | Structured JSON logging for production. Log levels by component. Request ID tracking. Sensitive field redaction |
| `config/production.yaml` | Production-specific engine config overrides (tighter cost limits, conservative energy thresholds) |
| `config/staging.yaml` | Staging config (mock embeddings, relaxed limits for testing) |
| `scripts/healthcheck.py` | Standalone health check script for Docker/k8s probes |

**Modified files:**

| File | Change |
|------|--------|
| `src/colloquip/config.py` | Add `Settings` class using pydantic-settings: validates all env vars at startup, typed, with defaults. Sections: `database`, `llm`, `embedding`, `memory`, `watchers`, `deployment` |
| `src/colloquip/api/app.py` | Add structured logging middleware. Add request ID header. Add CORS configuration for production origins |
| `pyproject.toml` | Add `pydantic-settings` to dependencies |

**Environment variables:**

```bash
# Required
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/colloquip
ANTHROPIC_API_KEY=sk-ant-...

# Optional (have defaults)
ENVIRONMENT=production          # development|staging|production
OPENAI_API_KEY=sk-...          # For embeddings (falls back to mock)
EMBEDDING_PROVIDER=openai       # mock|openai
MEMORY_STORE=pgvector           # in_memory|pgvector
LOG_LEVEL=INFO                  # DEBUG|INFO|WARNING|ERROR
LOG_FORMAT=json                 # json|text
CORS_ORIGINS=https://app.colloquip.io
MAX_COST_PER_THREAD_USD=5.0
MONTHLY_BUDGET_USD=500.0
WATCHER_POLL_INTERVAL=300       # seconds
REDIS_URL=redis://localhost:6379
```

---

### Sprint D4: Database Migration Strategy (Part of Sprint 11)

**Goal:** Safe, repeatable schema evolution for production deployments.

**Migration approach:**

1. **Baseline migration (001):** Captures all existing tables (sessions, posts, energy_history, consensus_maps, syntheses, cost_records, subreddits, agent_identities, subreddit_memberships) as the starting schema
2. **Phase 3 migrations (002-003):** `synthesis_memories`, `memory_annotations`, `typed_memories` tables. pgvector extension creation
3. **Phase 4 migrations (004):** `watchers`, `watcher_events`, `notifications` tables. `triggered_by` and `watcher_event_id` columns on `threads`
4. **Phase 5 migrations (005-006):** `cross_references`, `outcome_reports`, `agent_calibration` tables

**Migration safety rules:**
- All migrations are reversible (include `downgrade()`)
- No data-destructive operations without explicit backup step
- New columns are always nullable or have defaults (no breaking changes)
- Indexes created concurrently where possible (`CREATE INDEX CONCURRENTLY`)
- Migration tested in CI against empty DB and against populated DB

**Deployment flow:**
```
1. Deploy new code (but don't restart yet)
2. Run: alembic upgrade head
3. Verify migration: alembic current
4. Restart application
5. Smoke test health endpoint
```

---

### Sprint D5: Monitoring + Observability (After Sprint 17)

**Goal:** Production observability for Phase 3-5 systems.

**New files:**

| File | Purpose |
|------|---------|
| `src/colloquip/metrics.py` | Application metrics collection: deliberation count, latency, cost, memory retrieval hits, watcher events, triage decisions, error rates |
| `docker-compose.monitoring.yml` | Optional monitoring stack: Prometheus (scrape `/metrics`), Grafana (dashboards) |
| `config/grafana/dashboards/colloquip.json` | Pre-built Grafana dashboard: deliberation throughput, cost over time, memory store size, watcher activity, error rates |

**Modified files:**

| File | Change |
|------|--------|
| `src/colloquip/api/routes.py` | Add `GET /metrics` endpoint (Prometheus format) |
| `src/colloquip/engine.py` | Emit timing metrics for deliberation phases |
| `src/colloquip/memory/retriever.py` | Emit retrieval latency + hit rate metrics |
| `src/colloquip/watchers/manager.py` | Emit watcher poll + triage metrics |
| `pyproject.toml` | Add `prometheus-client` to optional `monitoring` dependency group |

**Key metrics:**

| Metric | Type | Description |
|--------|------|-------------|
| `colloquip_deliberations_total` | Counter | Total deliberations started |
| `colloquip_deliberation_duration_seconds` | Histogram | Deliberation wall-clock time |
| `colloquip_deliberation_cost_usd` | Histogram | Cost per deliberation |
| `colloquip_memory_retrievals_total` | Counter | Memory retrieval requests |
| `colloquip_memory_retrieval_latency_seconds` | Histogram | Vector search latency |
| `colloquip_memory_store_size` | Gauge | Total memories stored |
| `colloquip_watcher_events_total` | Counter | Events detected by watchers, by type |
| `colloquip_triage_decisions_total` | Counter | Triage decisions by signal level |
| `colloquip_notifications_total` | Counter | Notifications sent |
| `colloquip_llm_tokens_total` | Counter | LLM tokens used, by model |
| `colloquip_llm_errors_total` | Counter | LLM API errors |

---

## Dependency Graph

```
                     Sprint D1: Docker
                          │
                 Sprint D2: CI/CD ──────────────────────┐
                          │                              │
Sprint 8:  Embeddings + Vector Store                     │
     │                                                   │
Sprint 9:  Synthesis -> Memory Pipeline                  │
     │          │                                        │
Sprint 10: Prompt Integration (RAG)    Sprint D3: Config │
     │                                       │           │
Sprint 11: PostgreSQL + pgvector + Alembic ──┘           │
     │          (includes Sprint D4: Migrations)         │
Sprint 12: Human Memory Corrections                      │
     │                                                   │
Sprint 13: Phase 3 Validation ──────────────────┐        │
     │                                          │        │
Sprint 14: Watcher Models + Triage ◄────────────┤        │
     │                (can start parallel)       │        │
Sprint 15: Watcher Implementations              │        │
     │                                          │        │
Sprint 16: Notification System + API            │        │
     │                                          │        │
Sprint 17: Auto-Deliberation + Ph4 Valid. ──────┤        │
     │                                          │        │
     │                          Sprint D5: Monitoring    │
     │                                          │        │
Sprint 18: Cross-Subreddit References ◄─────────┘        │
     │                                                   │
Sprint 19: Outcome Tracking + Calibration (parallel w/18)│
     │                                                   │
Sprint 20: Export + External API + Ph5 Validation ───────┘
```

**Parallelization opportunities:**
- Sprint D1 (Docker) and D2 (CI/CD) can start immediately, parallel with Sprint 8
- Sprint D3 (Config) can run parallel with Sprints 9-10
- Sprint 11 (pgvector) includes D4 (migrations)
- Sprint 14 (watcher models) can start parallel with Sprints 11-13
- Sprints 18 and 19 can run in parallel
- Sprint D5 (monitoring) can start after Sprint 17

---

## New Dependencies by Sprint

| Sprint | Package | Optional Group | Purpose |
|--------|---------|---------------|---------|
| 11 | `asyncpg` | `db-pg` | Async PostgreSQL driver |
| 11 | `pgvector` | `db-pg` | pgvector SQLAlchemy integration |
| 11 | `openai` | `embeddings` | text-embedding-3-small |
| 11 | `alembic` | `db-pg` | Database migrations |
| D3 | `pydantic-settings` | (core) | Environment-based config |
| D5 | `prometheus-client` | `monitoring` | Metrics export |
| 20 | `weasyprint` | `export` | PDF export |

**Updated pyproject.toml optional groups:**

```toml
[project.optional-dependencies]
# ... existing groups ...
db-pg = [
    "asyncpg>=0.29",
    "pgvector>=0.3",
    "alembic>=1.13",
]
embeddings = [
    "openai>=1.0",
]
monitoring = [
    "prometheus-client>=0.20",
]
export = [
    "weasyprint>=62",
]
```

---

## Test Count Projection

| Sprint | Description | New Tests | Running Total |
|--------|-------------|-----------|---------------|
| 8 | Embeddings + Vector Store | ~20 | ~333 |
| 9 | Memory Pipeline | ~15 | ~348 |
| 10 | RAG Prompt Integration | ~10 | ~358 |
| 11 | pgvector + Alembic | ~15 | ~373 |
| 12 | Memory Corrections | ~12 | ~385 |
| 13 | Phase 3 Validation | ~8 | ~393 |
| 14 | Watcher Models + Triage | ~15 | ~408 |
| 15 | Watcher Implementations | ~18 | ~426 |
| 16 | Notification System | ~15 | ~441 |
| 17 | Auto-Deliberation | ~10 | ~451 |
| 18 | Cross-Subreddit Refs | ~12 | ~463 |
| 19 | Outcome + Calibration | ~12 | ~475 |
| 20 | Export + External API | ~10 | ~485 |
| D1-D5 | Infrastructure tests | ~8 | ~493 |

---

## File Change Summary (All Sprints)

### New Packages

| Package | Sprint | Files |
|---------|--------|-------|
| `src/colloquip/embeddings/` | 8 | `__init__.py`, `interface.py`, `mock.py`, `openai.py` |
| `src/colloquip/memory/` | 8-9 | `__init__.py`, `store.py`, `retriever.py`, `extractor.py`, `pgvector_store.py`, `cross_references.py`, `differ.py` |
| `src/colloquip/watchers/` | 14-15 | `__init__.py`, `interface.py`, `triage.py`, `literature.py`, `scheduled.py`, `webhook.py`, `manager.py`, `auto_deliberation.py` |
| `src/colloquip/notifications/` | 16 | `__init__.py`, `store.py` |
| `src/colloquip/feedback/` | 19 | `__init__.py`, `outcome.py`, `calibration.py` |
| `alembic/` | 11 | `env.py`, 6 migration files |

### New API Route Files

| File | Sprint | Endpoints |
|------|--------|-----------|
| `src/colloquip/api/memory_routes.py` | 12 | Memories, annotations, cross-references |
| `src/colloquip/api/watcher_routes.py` | 16 | Watchers, notifications, webhooks |
| `src/colloquip/api/feedback_routes.py` | 19 | Outcomes, calibration |
| `src/colloquip/api/export_routes.py` | 20 | Export markdown/JSON/PDF |
| `src/colloquip/api/external_routes.py` | 20 | External submit/poll |

### Infrastructure Files

| File | Sprint | Purpose |
|------|--------|---------|
| `Dockerfile` | D1 | Multi-stage production build |
| `Dockerfile.dev` | D1 | Development image |
| `docker-compose.yml` | D1 | App + Postgres + Redis |
| `docker-compose.dev.yml` | D1 | Dev overrides |
| `docker-compose.monitoring.yml` | D5 | Prometheus + Grafana |
| `.dockerignore` | D1 | Build exclusions |
| `.github/workflows/ci.yml` | D2 | Test + lint pipeline |
| `.github/workflows/deploy.yml` | D2 | Docker build + deploy |
| `.github/workflows/db-migration.yml` | D2 | Migration validation |
| `.env.example` | D3 | Environment template |
| `config/production.yaml` | D3 | Production config |
| `config/staging.yaml` | D3 | Staging config |
| `scripts/healthcheck.py` | D3 | Health check probe |
| `alembic.ini` | 11 | Alembic configuration |

### Modified Existing Files

| File | Sprints | Summary of Changes |
|------|---------|-------------------|
| `src/colloquip/models.py` | 12, 13, 14 | `MemoryAnnotationType`, `MemoryType`, `MemoryScope`, `TypedMemory`, `WatcherType`, `WatcherConfig`, `WatcherEvent`, `TriageDecision` |
| `src/colloquip/agents/prompts.py` | 10 | `build_memory_context()`, prior_deliberations parameter |
| `src/colloquip/engine.py` | 9, 10 | Memory storage after synthesis, memory retrieval before deliberation |
| `src/colloquip/api/app.py` | 9, 12, 16, 19, 20 | Mount new route files, WatcherManager background task |
| `src/colloquip/api/ws.py` | 9, 10, 16 | New event types: `memory_stored`, `memories_retrieved`, `notification` |
| `src/colloquip/api/platform_manager.py` | 9 | Memory store + embedding provider, `store_synthesis_memory()` |
| `src/colloquip/api/routes.py` | D1 | `/health` and `/metrics` endpoints |
| `src/colloquip/db/tables.py` | 11, 12, 16, 18, 19 | 8 new DB table models |
| `src/colloquip/db/repository.py` | 11, 12, 16 | Memory, annotation, watcher, notification CRUD |
| `src/colloquip/config.py` | 11, D3 | `Settings` class, env var validation, deployment config |
| `pyproject.toml` | 11, D3, D5, 20 | New optional dependency groups |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Embedding quality too low for useful retrieval | Medium | High | Mock embeddings for testing; swap providers via config without code changes |
| pgvector migration breaks existing SQLite tests | Low | High | Keep SQLite for unit tests, pgvector for integration tests only. CI runs both |
| Triage agent too many false positives | Medium | Medium | Conservative defaults (notify, don't auto-act). Earned auto-deliberation |
| Cross-reference detection too noisy | Medium | Medium | Strict triple criteria (similarity AND entity AND actionable). Human review required |
| Typed memory extraction <85% quality | High | Medium | Phase 3b gated on calibration. Don't ship until quality proven empirically |
| PubMed watcher rate-limited | Low | Low | Respect NCBI limits. Configurable poll intervals. Response caching |
| Docker image too large | Low | Low | Multi-stage build. Separate optional deps. `.dockerignore` |
| CI too slow | Medium | Low | Parallel jobs. Cache uv deps. Skip integration tests on draft PRs |
| Migration conflicts between developers | Medium | Medium | Linear migration numbering. CI validates migration chain. Merge-queue discipline |
| Redis single point of failure (watchers) | Low | Medium | Watcher state recoverable from DB. Redis only caches poll timestamps |

---

## What We Explicitly Defer Beyond Phase 5

| Feature | Reason |
|---------|--------|
| Agent persona evolution | Requires significant R&D; risks persona drift |
| Optimal panel composition | Combinatorial optimization needs outcome tracking data first |
| Dynamic agent creation | Quality control problem unsolved |
| Multi-modal evidence | Requires multi-modal LLM + new tool adapters |
| Adversarial robustness | Research question, not engineering task |
| Kubernetes deployment | Docker Compose sufficient until scale demands it |
| Multi-tenancy / auth | Out of scope for scientific platform MVP |

---

*Phase 3-5 Implementation Plan v1.0*
*Depends on: Phase 1-2 completion (313 tests passing)*
*Created: 2026-02-12*
