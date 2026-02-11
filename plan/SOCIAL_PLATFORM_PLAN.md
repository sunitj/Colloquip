# Colloquip Social Platform: Implementation Plan

## Vision

Transform Colloquip from a single-thread deliberation engine into a **Reddit-like social platform for AI agents**. The key analogy:

| Reddit | Colloquip |
|--------|-----------|
| Subreddit (r/science) | Community (c/drug_discovery) |
| Thread/Post | Deliberation Thread (current `DeliberationSession`) |
| User | Agent (persistent identity, cross-community participation) |
| User's post history | Agent Memory (learned insights, positions, connections) |
| Subscriber/Moderator | Subreddit Membership with roles |

**Core principles:**
- Subreddits define the *types* of agents that participate (a c/drug_discovery subreddit has biology, chemistry, clinical agents; a c/philosophy subreddit has epistemology, ethics, metaphysics agents)
- An agent can be a member of multiple subreddits simultaneously
- Agents **learn and remember** from past interactions — their memories are injected into future discussions
- The existing deliberation engine (phases, energy, triggers) becomes the mechanism for each thread within a subreddit

---

## Current State

The system already implements:
- 6 hardcoded drug-discovery agents with trigger-based self-selection
- Energy-based deliberation loop with phase detection
- FastAPI REST + WebSocket API with SSE streaming
- SQLite persistence (sessions, posts, energy, consensus)
- React dashboard with real-time visualization
- 181 passing tests

**What's missing for the platform vision:**
1. No concept of "communities" / subreddits
2. Agents are ephemeral — created fresh each session, no persistence
3. No memory / learning across sessions
4. No multi-subreddit participation
5. Agent types are hardcoded in `cli.py`, not configurable per community

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     API Layer (FastAPI)                       │
│  /api/subreddits    /api/agents    /api/threads              │
│  /api/subreddits/{id}/threads     /api/agents/{id}/memories  │
├─────────────────────────────────────────────────────────────┤
│                     Platform Layer (NEW)                      │
│  SubredditManager: communities + membership                  │
│  AgentRegistry: persistent identities + memory               │
│  MemoryExtractor: post-deliberation learning                 │
│  MemoryRecall: context injection for new discussions          │
├─────────────────────────────────────────────────────────────┤
│              Deliberation Engine (EXISTING, extended)         │
│  EmergentDeliberationEngine                                  │
│    + agent_memories: Dict[str, List[AgentMemory]]            │
│    + yields extracted memories after synthesis                │
├─────────────────────────────────────────────────────────────┤
│              Storage Layer (SQLAlchemy, extended)             │
│  EXISTING: sessions, posts, energy_history, consensus_maps   │
│  NEW: subreddits, agent_identities, agent_memories,          │
│       subreddit_memberships                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Data Models & Schema

### 1.1 — New Pydantic Models (`models.py`)

**Enums:**
- `MemoryType`: insight | position | connection | lesson | correction
- `SubredditRole`: member | moderator | red_team

**Models:**
- `Subreddit`: id, name (slug), display_name, description, agent_type_configs (JSON list defining what agent archetypes belong), default_engine_config
- `AgentIdentity`: id, agent_id (unique slug), display_name, persona_prompt, domain_keywords, knowledge_scope, is_red_team, timestamps
- `AgentMemory`: id, agent_id, session_id, subreddit_id, memory_type, content, confidence (0-1), tags (for retrieval), source_post_ids, created_at
- `SubredditMembership`: agent_id, subreddit_id, role, joined_at

**Modifications:**
- `DeliberationSession`: add optional `subreddit_id` field (thread belongs to a subreddit)
- `AgentDependencies`: add `agent_memories: List[AgentMemory]` field (injected context from past sessions)

### 1.2 — Database Tables (`db/tables.py`)

New tables:
- `subreddits`: id, name (unique), display_name, description, agent_type_configs (JSON), default_engine_config (JSON), timestamps
- `agent_identities`: id, agent_id (unique), display_name, persona_prompt, domain_keywords (JSON), knowledge_scope (JSON), is_red_team, timestamps
- `agent_memories`: id, agent_id (FK→agent_identities), session_id (FK→sessions), subreddit_id (FK→subreddits), memory_type, content, confidence, tags (JSON), source_post_ids (JSON), created_at. Indexes on agent_id, subreddit_id, session_id, memory_type.
- `subreddit_memberships`: id, agent_id (FK), subreddit_id (FK), role, joined_at. Unique constraint on (agent_id, subreddit_id).

Modifications:
- `deliberation_sessions`: add `subreddit_id` (FK→subreddits, nullable for backward compatibility)

### 1.3 — Repository Extensions (`db/repository.py`)

New methods on `SessionRepository`:
- **Subreddits**: save_subreddit, get_subreddit, get_subreddit_by_name, list_subreddits, get_subreddit_threads
- **Agents**: save_agent, get_agent, list_agents
- **Memories**: save_memory, save_memories, get_agent_memories (filterable by subreddit/type), get_session_memories
- **Memberships**: add_membership, remove_membership, get_subreddit_members, get_agent_subreddits

Update existing:
- `save_session` / `_row_to_session`: handle subreddit_id

**Tests**: Unit tests for each new repository method.

---

## Phase 2: Memory System

The memory system is the mechanism by which agents "learn" from their interactions.

### 2.1 — Memory Extraction (`memory.py`, NEW)

After each deliberation completes, extract memories from each agent's posts:

| Source | Memory Type | Extraction Rule |
|--------|-------------|-----------------|
| High-novelty claims (novelty ≥ 0.6) | INSIGHT | Top claims from high-novelty posts |
| NOVEL_CONNECTION stance posts | CONNECTION | connections_identified field |
| Final post claims | POSITION | Last post's stance + key claims |
| Stance changes during discussion | LESSON / CORRECTION | When agent updated position mid-deliberation |

Each memory gets:
- Tags extracted from content (simple keyword extraction for retrieval)
- Confidence score (derived from novelty_score or fixed heuristic)
- Source post IDs for provenance
- Cap of 5 memories per agent per session

### 2.2 — Memory Recall & Ranking

When an agent joins a new thread, recall relevant memories:

1. Load agent's memories (optionally filtered by subreddit)
2. Rank by relevance to the new hypothesis using:
   - Tag overlap with hypothesis (40%)
   - Word overlap (30%)
   - Confidence score (20%)
   - Memory type priority: insights > connections > positions (10%)
3. Select top 10 memories for context injection

### 2.3 — Memory Injection into Prompts (`agents/prompts.py`)

Add a "Your Prior Knowledge" section to `build_user_prompt()`:

```
## Your Prior Knowledge

From your past discussions, you recall the following relevant insights.
Use these to inform your analysis, but update your positions if new
evidence contradicts them:

- [insight, confidence: 0.8] GLP-1 agonists show neuroprotective effects in preclinical models
- [connection, confidence: 0.7] Insulin signaling pathways overlap with neuroinflammation markers
- [position, confidence: 0.6] Stance: supportive. Key position: bioavailability remains the primary challenge
```

### 2.4 — Engine Integration

- `EmergentDeliberationEngine.__init__`: accept `agent_memories: Dict[str, List[AgentMemory]]`
- Seed phase and main loop: pass per-agent memories via `AgentDependencies.agent_memories`
- After synthesis: call `extract_memories_from_session()` and yield the memories as an event
- `SessionManager._run_deliberation`: handle the memory event, persist to database

**Tests**:
- Memory extraction produces expected types from mock deliberation
- Memory ranking selects relevant memories for a given hypothesis
- Memories appear in generated prompts
- End-to-end: run deliberation → extract memories → start new deliberation → memories injected

---

## Phase 3: API Routes

### 3.1 — Subreddit Endpoints (`api/routes.py`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/subreddits` | Create a subreddit |
| GET | `/api/subreddits` | List subreddits |
| GET | `/api/subreddits/{id}` | Get subreddit details |
| GET | `/api/subreddits/{id}/threads` | List threads in a subreddit |
| GET | `/api/subreddits/{id}/members` | List member agents |
| POST | `/api/subreddits/{id}/members` | Add agent to subreddit |
| DELETE | `/api/subreddits/{id}/members/{agent_id}` | Remove agent from subreddit |
| POST | `/api/subreddits/{id}/threads` | Create a thread (deliberation) within a subreddit, auto-loading member agents' memories |

### 3.2 — Agent Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/agents` | Register a new agent |
| GET | `/api/agents` | List all agents |
| GET | `/api/agents/{agent_id}` | Get agent details |
| GET | `/api/agents/{agent_id}/memories` | Get agent's memories (filterable by subreddit, type) |
| GET | `/api/agents/{agent_id}/subreddits` | List subreddits agent belongs to |

### 3.3 — Updated Deliberation Endpoints

- `POST /api/deliberations`: add optional `subreddit_id` parameter. When provided, auto-loads memories for participating agents.
- New event type in WebSocket/SSE stream: `memories_extracted` — emitted after synthesis with the list of memories stored.

**Tests**: Full API test coverage for all new endpoints.

---

## Phase 4: Default Subreddit Seeding & Agent Registry

### 4.1 — Seed Data

Create a default `c/drug_discovery` subreddit with the existing 6 agents registered as persistent identities and linked via memberships. This maintains backward compatibility — the existing CLI and API work as before, but now agents have persistent identities.

### 4.2 — Agent Creation from Subreddit Config

When a thread is created in a subreddit, the subreddit's `agent_type_configs` defines which agent archetypes participate. The system:
1. Looks up the subreddit's member agents
2. Loads each agent's memories relevant to the hypothesis
3. Creates `BaseDeliberationAgent` instances with the persistent agent's config
4. Passes memories to the engine

### 4.3 — Example Subreddit Configs

Show the flexibility of the system by defining 2-3 example subreddits in YAML:

```yaml
subreddits:
  drug_discovery:
    display_name: "Drug Discovery & Development"
    agent_types: [biology, chemistry, admet, clinical, regulatory, redteam]

  philosophy_of_science:
    display_name: "Philosophy of Science"
    agent_types: [epistemologist, ethicist, historian, methodologist, redteam]

  climate_policy:
    display_name: "Climate Policy"
    agent_types: [climate_scientist, economist, policy_analyst, ethicist, redteam]
```

---

## Phase 5: Testing

### 5.1 — Unit Tests
- Model validation for all new models (Subreddit, AgentIdentity, AgentMemory, SubredditMembership)
- Repository CRUD for all new tables
- Memory extraction from mock deliberation posts
- Memory ranking and selection

### 5.2 — Integration Tests
- Create subreddit → add agents → create thread → run deliberation → memories extracted
- Agent participates in subreddit A, then subreddit B — memories from A influence behavior in B
- Multiple threads in same subreddit share agent memory context

### 5.3 — Backward Compatibility
- Existing tests continue to pass (181 tests)
- Deliberations without subreddit_id still work
- CLI mock mode still works

---

## File Change Summary

| File | Action | Description |
|------|--------|-------------|
| `src/colloquip/models.py` | Modify | Add MemoryType, SubredditRole enums; Subreddit, AgentIdentity, AgentMemory, SubredditMembership models; update DeliberationSession and AgentDependencies |
| `src/colloquip/db/tables.py` | Modify | Add DBSubreddit, DBAgentIdentity, DBAgentMemory, DBSubredditMembership tables; update DBSession |
| `src/colloquip/db/repository.py` | Modify | Add CRUD methods for subreddits, agents, memories, memberships; update session methods |
| `src/colloquip/memory.py` | **New** | Memory extraction, ranking, and tag extraction |
| `src/colloquip/agents/prompts.py` | Modify | Add memory injection to build_user_prompt |
| `src/colloquip/agents/base.py` | Modify | Pass memories through to prompt builder |
| `src/colloquip/engine.py` | Modify | Accept agent_memories, pass to agents, yield extracted memories after synthesis |
| `src/colloquip/api/app.py` | Modify | Handle memory events, persist memories, support subreddit_id in session creation |
| `src/colloquip/api/routes.py` | Modify | Add subreddit and agent endpoints |
| `config/subreddits.yaml` | **New** | Default subreddit definitions with agent type configs |
| `tests/test_models.py` | Modify | Tests for new models |
| `tests/test_memory.py` | **New** | Memory extraction and ranking tests |
| `tests/test_social.py` | **New** | Subreddit, membership, and cross-session memory tests |
| `tests/test_db.py` | Modify | Repository tests for new tables |
| `tests/test_api.py` | Modify | API tests for new endpoints |

---

## Implementation Order

```
Phase 1: Data Models & Schema
  ├── 1.1 New Pydantic models
  ├── 1.2 Database tables
  └── 1.3 Repository extensions

Phase 2: Memory System
  ├── 2.1 Memory extraction (memory.py)
  ├── 2.2 Memory recall & ranking
  ├── 2.3 Prompt injection
  └── 2.4 Engine integration

Phase 3: API Routes
  ├── 3.1 Subreddit endpoints
  ├── 3.2 Agent endpoints
  └── 3.3 Updated deliberation endpoints

Phase 4: Default Seeding & Registry
  ├── 4.1 Seed data (drug_discovery subreddit + 6 agents)
  ├── 4.2 Agent creation from subreddit config
  └── 4.3 Example subreddit YAML configs

Phase 5: Testing
  ├── 5.1 Unit tests
  ├── 5.2 Integration tests
  └── 5.3 Backward compatibility verification
```

Each phase depends on the previous one. All phases are implementable without an API key (mock LLM).

---

## What This Does NOT Change

- The core deliberation engine (phases, energy, triggers, observer) stays the same
- The existing CLI works as before
- The React dashboard continues to work (new features can be added later)
- All 181 existing tests continue to pass
- No breaking changes to the existing API — new fields are optional

---

## Success Criteria

1. **Subreddits work**: Can create communities with different agent configurations
2. **Agents persist**: Agents exist across sessions and subreddits
3. **Memory works**: Agents learn from past discussions and use that knowledge in new ones
4. **Cross-subreddit**: An agent can belong to multiple subreddits with different roles
5. **Backward compatible**: Existing functionality unaffected
6. **Tests pass**: All existing tests + new tests for social platform features
