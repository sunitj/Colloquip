# System Design: Emergent Deliberation Architecture

> **Wiki**: See [Architecture Overview](https://github.com/sunitj/Colloquip/wiki/Architecture-Overview) for a high-level summary with layered architecture and data flow narrative. This document contains the detailed component interfaces and Pydantic model definitions.

This document describes the complete system architecture for the emergent deliberation system, from data flow to component interfaces.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       FRONTEND (React 19 + Vite)                         │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌───────────────┐  │
│  │ Hypothesis  │  │ Deliberation │  │   Phase     │  │   Energy      │  │
│  │   Input     │  │    Forum     │  │  Indicator  │  │  Dashboard    │  │
│  └──────┬──────┘  └──────┬───────┘  └──────┬──────┘  └───────┬───────┘  │
│         │                │                 │                  │          │
└─────────┼────────────────┼─────────────────┼──────────────────┼──────────┘
          │                │                 │                  │
          └────────────────┴─────────────────┴──────────────────┘
                                    │
                           WebSocket / SSE
                                    │
┌───────────────────────────────────┴─────────────────────────────────────┐
│                           API LAYER (FastAPI)                            │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────────┐  │
│  │  /deliberations │  │  /ws/deliberation │  │  /deliberations/{id}  │  │
│  │     POST        │  │   WebSocket       │  │    /intervene POST    │  │
│  └────────┬────────┘  └─────────┬─────────┘  └───────────┬───────────┘  │
│           │                     │                        │               │
└───────────┼─────────────────────┼────────────────────────┼───────────────┘
            │                     │                        │
            └─────────────────────┼────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    EMERGENT DELIBERATION ENGINE                          │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                        MAIN LOOP                                    │ │
│  │                                                                     │ │
│  │  1. OBSERVER detects phase from metrics                            │ │
│  │  2. AGENTS evaluate triggers, select responders                    │ │
│  │  3. RESPONDERS generate posts concurrently                         │ │
│  │  4. ENERGY calculated, termination checked                         │ │
│  │  5. POSTS streamed to frontend                                     │ │
│  │  6. Loop until TERMINATION → SYNTHESIS                             │ │
│  │                                                                     │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────────┐ │
│  │  OBSERVER  │  │  AGENTS    │  │  ENERGY    │  │  KNOWLEDGE         │ │
│  │            │  │  (x6)      │  │ CALCULATOR │  │  SERVICE           │ │
│  └────────────┘  └────────────┘  └────────────┘  └────────────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────────────┐ │
│  │   PostgreSQL    │  │    pgvector     │  │      LLM Gateway         │ │
│  │   (sessions,    │  │  (knowledge     │  │   (Anthropic/OpenAI)     │ │
│  │    posts)       │  │   embeddings)   │  │                          │ │
│  └─────────────────┘  └─────────────────┘  └──────────────────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Component Interfaces

### 1. Deliberation Engine

The core orchestrator that runs the emergent loop.

```python
class EmergentDeliberationEngine:
    """
    Main engine for emergent deliberation.

    Replaces hardcoded phase sequence with:
    - Observer-based phase detection
    - Trigger-based agent selection
    - Energy-based termination
    """

    def __init__(
        self,
        agents: Dict[str, BaseDeliberationAgent],
        observer: ObserverAgent,
        knowledge_service: KnowledgeService,
        energy_calculator: EnergyCalculator,
        config: EngineConfig
    ):
        self.agents = agents
        self.observer = observer
        self.knowledge_service = knowledge_service
        self.energy_calculator = energy_calculator
        self.config = config

    async def run_deliberation(
        self,
        session: DeliberationSession,
        hypothesis: str
    ) -> AsyncIterator[Union[Post, PhaseSignal, EnergyUpdate]]:
        """
        Run emergent deliberation.

        Yields:
            Post: Agent or observer posts
            PhaseSignal: Phase transitions
            EnergyUpdate: Energy level updates
        """
        ...

    async def handle_intervention(
        self,
        session_id: str,
        intervention: HumanIntervention
    ) -> AsyncIterator[Post]:
        """Handle human intervention mid-deliberation."""
        ...
```

### 2. Observer Agent

Meta-agent that detects phases from conversation dynamics.

```python
class ObserverAgent:
    """
    Observer agent for phase detection.

    Does NOT participate in scientific discussion.
    ONLY observes dynamics and broadcasts phase state.
    """

    def __init__(
        self,
        energy_calculator: EnergyCalculator,
        config: ObserverConfig
    ):
        self.energy_calculator = energy_calculator
        self.config = config
        self.current_phase = Phase.EXPLORE
        self.pending_phase: Optional[Phase] = None
        self.pending_count = 0

    def detect_phase(self, posts: List[Post]) -> PhaseSignal:
        """
        Detect current phase from post dynamics.

        Returns:
            PhaseSignal with current_phase, confidence, metrics, observation
        """
        ...

    def should_terminate(self, posts: List[Post]) -> Tuple[bool, str]:
        """
        Check if deliberation should end.

        Returns:
            (should_terminate, reason)
        """
        ...
```

### 3. Base Deliberation Agent

Foundation for all scientist agents.

```python
class BaseDeliberationAgent:
    """
    Base class for all deliberation agents.

    Each agent has:
    - Core persona (static identity)
    - Phase mandates (dynamic behavior)
    - Trigger rules (self-selection)
    - Knowledge access (RAG tools)
    """

    def __init__(
        self,
        agent_id: str,
        display_name: str,
        persona_prompt: str,
        phase_mandates: Dict[Phase, str],
        domain_keywords: List[str],
        knowledge_scope: List[str],
        evaluation_criteria: Dict[str, float],
        model: str = "anthropic:claude-sonnet-4-20250514"
    ):
        ...

    async def should_respond(
        self,
        posts: List[Post],
        phase: Phase
    ) -> Tuple[bool, List[str]]:
        """
        Evaluate trigger rules.

        Returns:
            (should_respond, list of triggered rules)
        """
        ...

    async def generate_post(
        self,
        deps: AgentDependencies
    ) -> AgentPost:
        """
        Generate a post given current context.

        Args:
            deps: AgentDependencies with session, phase, posts, knowledge

        Returns:
            AgentPost with content, stance, citations, etc.
        """
        ...

    def _build_system_prompt(self, phase: Phase) -> str:
        """Build phase-aware system prompt."""
        ...
```

### 4. Energy Calculator

Computes conversation energy for termination decisions.

```python
class EnergyCalculator:
    """
    Calculate conversation energy from post dynamics.
    """

    def __init__(self, config: EnergyConfig):
        self.config = config

    def calculate_energy(self, posts: List[Post]) -> float:
        """
        Calculate current energy level (0.0 - 1.0).
        """
        ...

    def calculate_metrics(self, posts: List[Post]) -> ConversationMetrics:
        """
        Calculate detailed conversation metrics.
        """
        ...
```

### 5. Trigger Evaluator

Evaluates trigger rules for agent self-selection.

```python
class TriggerEvaluator:
    """
    Evaluate trigger rules for an agent.
    """

    def __init__(
        self,
        agent_id: str,
        domain_keywords: List[str],
        knowledge_scope: List[str],
        is_red_team: bool = False
    ):
        ...

    def evaluate(
        self,
        posts: List[Post],
        phase: Phase
    ) -> Tuple[bool, List[str]]:
        """
        Evaluate all trigger rules.

        Returns:
            (should_respond, list of triggered rules)
        """
        ...
```

---

## Data Models

### Core Models

```python
from enum import Enum
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict
from uuid import UUID


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


class Citation(BaseModel):
    document_id: str
    title: str
    excerpt: str
    relevance: float


class Post(BaseModel):
    id: UUID
    session_id: UUID
    agent_id: str
    content: str
    stance: AgentStance
    citations: List[Citation]
    key_claims: List[str]
    questions_raised: List[str]
    connections_identified: List[str]
    novelty_score: float
    phase: Phase
    triggered_by: List[str]  # Which rules triggered this post
    created_at: datetime


class ConversationMetrics(BaseModel):
    question_rate: float
    disagreement_rate: float
    topic_diversity: float
    citation_density: float
    novelty_avg: float
    energy: float
    posts_since_novel: int


class PhaseSignal(BaseModel):
    current_phase: Phase
    confidence: float
    metrics: ConversationMetrics
    observation: Optional[str]


class EnergyUpdate(BaseModel):
    turn: int
    energy: float
    components: Dict[str, float]  # novelty, disagreement, questions, staleness


class DeliberationSession(BaseModel):
    id: UUID
    hypothesis: str
    status: str  # pending, running, paused, completed
    phase: Phase
    config: Dict
    created_at: datetime
    updated_at: datetime


class ConsensusMap(BaseModel):
    session_id: UUID
    summary: str
    agreements: List[str]
    disagreements: List[str]
    minority_positions: List[str]
    serendipity_connections: List[Dict]
    final_stances: Dict[str, AgentStance]
    created_at: datetime
```

### Agent Configuration

```python
class AgentConfig(BaseModel):
    agent_id: str
    display_name: str
    persona_prompt: str
    phase_mandates: Dict[Phase, str]
    domain_keywords: List[str]
    knowledge_scope: List[str]
    evaluation_criteria: Dict[str, float]
    is_red_team: bool = False


class EngineConfig(BaseModel):
    max_turns: int = 30
    min_posts: int = 12
    energy_threshold: float = 0.2
    low_energy_rounds: int = 3
    refractory_period: int = 2
    hysteresis_threshold: int = 2
    phase_max_tokens: Dict[str, int] = {
        "explore": 1024, "debate": 1280, "deepen": 1024,
        "converge": 768, "synthesis": 2048,
    }
```

---

## Data Flow

### 1. Deliberation Start

```
User submits hypothesis
         │
         ▼
┌─────────────────────┐
│  Create Session     │
│  Store in DB        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Initialize Engine  │
│  - Create agents    │
│  - Create observer  │
│  - Reset state      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Run Seed Phase     │
│  - All agents post  │
│  - Stream to client │
└──────────┬──────────┘
           │
           ▼
     Enter Main Loop
```

### 2. Main Loop (Each Turn)

```
┌─────────────────────────────────────────────────────────────────────┐
│                           TURN N                                     │
│                                                                      │
│  1. OBSERVER                                                         │
│     ┌──────────────────────────────────────────┐                    │
│     │  Calculate metrics from posts             │                    │
│     │  Detect phase (with hysteresis)           │                    │
│     │  Generate observation (optional)          │                    │
│     │  Return PhaseSignal                       │                    │
│     └─────────────────┬────────────────────────┘                    │
│                       │                                              │
│  2. TERMINATION CHECK │                                              │
│     ┌─────────────────┴────────────────────────┐                    │
│     │  Check energy threshold                   │                    │
│     │  Check max turns                          │                    │
│     │  If terminate → go to SYNTHESIS           │                    │
│     └─────────────────┬────────────────────────┘                    │
│                       │                                              │
│  3. TRIGGER EVALUATION (parallel)                                    │
│     ┌─────────────────┴────────────────────────┐                    │
│     │  For each agent:                          │                    │
│     │    - Check refractory period              │                    │
│     │    - Evaluate trigger rules               │                    │
│     │    - Collect responding agents            │                    │
│     └─────────────────┬────────────────────────┘                    │
│                       │                                              │
│  4. RESPONSE GENERATION (concurrent)                                 │
│     ┌─────────────────┴────────────────────────┐                    │
│     │  For each responding agent:               │                    │
│     │    - Build phase-aware prompt             │                    │
│     │    - Query knowledge base                 │                    │
│     │    - Generate post via LLM                │                    │
│     │    - Score novelty                        │                    │
│     └─────────────────┬────────────────────────┘                    │
│                       │                                              │
│  5. UPDATE & STREAM                                                  │
│     ┌─────────────────┴────────────────────────┐                    │
│     │  Add posts to history                     │                    │
│     │  Update energy history                    │                    │
│     │  Stream posts to client                   │                    │
│     │  Store in database                        │                    │
│     └─────────────────┬────────────────────────┘                    │
│                       │                                              │
│  6. LOOP              │                                              │
│     └─────────────────┴──────────────────────── → TURN N+1          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 3. Synthesis Phase

```
Termination triggered
         │
         ▼
┌─────────────────────┐
│  Collect all posts  │
│  Group by stance    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Extract:           │
│  - Agreements       │
│  - Disagreements    │
│  - Minority views   │
│  - Connections      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Generate summary   │
│  via LLM            │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Create ConsensusMap│
│  Store in DB        │
│  Stream to client   │
└──────────┬──────────┘
           │
           ▼
     Session Complete
```

---

## API Endpoints

### REST Endpoints

```python
# Create new deliberation session
@router.post("/api/deliberations")
async def create_deliberation(
    request: CreateDeliberationRequest
) -> DeliberationSession:
    """Create a new deliberation session."""
    ...

# Start deliberation with streaming
@router.post("/api/deliberations/{session_id}/start")
async def start_deliberation(
    session_id: UUID,
    config: Optional[EngineConfig] = None
) -> StreamingResponse:
    """
    Start deliberation with Server-Sent Events streaming.

    Streams:
    - Posts as they're generated
    - Phase transitions
    - Energy updates
    - Final ConsensusMap
    """
    ...

# Human intervention
@router.post("/api/deliberations/{session_id}/intervene")
async def intervene(
    session_id: UUID,
    intervention: HumanIntervention
) -> List[Post]:
    """
    Inject human intervention.

    Types:
    - question: Ask agents a question
    - data: Provide new data/evidence
    - redirect: Shift focus
    - terminate: Force synthesis
    """
    ...

# Get session state
@router.get("/api/deliberations/{session_id}")
async def get_deliberation(session_id: UUID) -> DeliberationState:
    """Get current state of deliberation."""
    ...

# Get energy history
@router.get("/api/deliberations/{session_id}/energy")
async def get_energy(session_id: UUID) -> List[EnergyUpdate]:
    """Get energy history for visualization."""
    ...
```

### WebSocket Endpoint

```python
@router.websocket("/api/ws/deliberation/{session_id}")
async def websocket_deliberation(
    websocket: WebSocket,
    session_id: UUID
):
    """
    WebSocket for real-time deliberation updates.

    Client → Server:
    - {"action": "start", "hypothesis": "...", "config": {...}}
    - {"action": "intervene", "type": "question", "content": "..."}
    - {"action": "pause"}
    - {"action": "resume"}

    Server → Client:
    - {"type": "post", "post": {...}}
    - {"type": "phase", "phase": "debate", "confidence": 0.8}
    - {"type": "energy", "energy": 0.65, "components": {...}}
    - {"type": "complete", "consensus_map": {...}}
    - {"type": "error", "message": "..."}
    """
    ...
```

---

## Database Schema

```sql
-- Sessions table
CREATE TABLE deliberation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hypothesis TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    current_phase VARCHAR(20) DEFAULT 'explore',
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Posts table
CREATE TABLE posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES deliberation_sessions(id),
    agent_id VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    stance VARCHAR(20) NOT NULL,
    citations JSONB DEFAULT '[]',
    key_claims JSONB DEFAULT '[]',
    questions_raised JSONB DEFAULT '[]',
    connections_identified JSONB DEFAULT '[]',
    novelty_score FLOAT DEFAULT 0.0,
    phase VARCHAR(20) NOT NULL,
    triggered_by JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_posts_session ON posts(session_id);
CREATE INDEX idx_posts_agent ON posts(agent_id);
CREATE INDEX idx_posts_phase ON posts(phase);

-- Energy history table
CREATE TABLE energy_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES deliberation_sessions(id),
    turn INT NOT NULL,
    energy FLOAT NOT NULL,
    novelty FLOAT,
    disagreement FLOAT,
    questions FLOAT,
    staleness FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_energy_session ON energy_history(session_id);

-- Consensus maps table
CREATE TABLE consensus_maps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES deliberation_sessions(id) UNIQUE,
    summary TEXT NOT NULL,
    agreements JSONB DEFAULT '[]',
    disagreements JSONB DEFAULT '[]',
    minority_positions JSONB DEFAULT '[]',
    serendipity_connections JSONB DEFAULT '[]',
    final_stances JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Knowledge items (existing, for RAG)
CREATE TABLE knowledge_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source_type VARCHAR(50),
    domain_tags TEXT[] DEFAULT '{}',
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_knowledge_embedding ON knowledge_items
    USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_knowledge_domains ON knowledge_items
    USING GIN (domain_tags);
```

---

## Configuration

### Environment Variables

```bash
# LLM Configuration
LLM_MODE=real                    # real or mock
ANTHROPIC_API_KEY=sk-...
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/colloquium

# Embeddings
USE_LOCAL_EMBEDDINGS=false
OPENAI_API_KEY=sk-...           # For embeddings if not local

# Engine Defaults
DEFAULT_MAX_TURNS=30
DEFAULT_MIN_POSTS=12
DEFAULT_ENERGY_THRESHOLD=0.2
```

### Configuration Files

```yaml
# config/agents.yaml
agents:
  biology:
    display_name: "Biology & Target ID"
    knowledge_scope: ["biology", "preclinical"]
    domain_keywords:
      - mechanism
      - target
      - pathway
      # ...

  chemistry:
    display_name: "Discovery Chemistry"
    knowledge_scope: ["chemistry", "manufacturing"]
    # ...

# config/engine.yaml
engine:
  max_turns: 30
  min_posts: 12
  energy_threshold: 0.2
  low_energy_rounds: 3
  refractory_period: 2
  phase_max_tokens:
    explore: 1024
    debate: 1280
    deepen: 1024
    converge: 768
    synthesis: 2048

observer:
  hysteresis_threshold: 2
  window_size: 5
  observation_frequency: 0.5

energy:
  weights:
    novelty: 0.4
    disagreement: 0.3
    questions: 0.2
    staleness: -0.1
```

---

## Error Handling

### Agent Failures

```python
async def _generate_with_retry(
    agent: BaseDeliberationAgent,
    deps: AgentDependencies,
    max_retries: int = 3
) -> Optional[Post]:
    """Generate post with retry logic."""
    for attempt in range(max_retries):
        try:
            return await agent.generate_post(deps)
        except RateLimitError:
            await asyncio.sleep(2 ** attempt)
        except Exception as e:
            logger.error(f"Agent {agent.agent_id} failed: {e}")
            if attempt == max_retries - 1:
                return None
    return None
```

### Graceful Degradation

If agents fail:
- Continue with remaining agents
- Log failure for debugging
- Don't block deliberation on single agent

If Observer fails:
- Fall back to previous phase
- Continue with last-known-good state

If energy calculation fails:
- Use default energy (0.5)
- Log warning

---

## Monitoring

### Metrics to Track

```python
# Prometheus metrics
deliberation_turns_total = Counter(
    "deliberation_turns_total",
    "Total deliberation turns",
    ["session_id", "phase"]
)

agent_response_time = Histogram(
    "agent_response_time_seconds",
    "Time for agent to generate response",
    ["agent_id"]
)

trigger_fires_total = Counter(
    "trigger_fires_total",
    "Trigger rule activations",
    ["agent_id", "rule"]
)

phase_transitions_total = Counter(
    "phase_transitions_total",
    "Phase transitions",
    ["from_phase", "to_phase"]
)

energy_level = Gauge(
    "energy_level",
    "Current conversation energy",
    ["session_id"]
)
```

### Logging

```python
# Structured logging
logger.info(
    "Turn completed",
    extra={
        "session_id": session_id,
        "turn": turn,
        "phase": phase.value,
        "responding_agents": [a.agent_id for a in responding],
        "energy": energy,
        "posts_generated": len(new_posts),
    }
)
```

---

## Testing Strategy

### Unit Tests

```python
# Test energy calculation
def test_energy_high_novelty():
    posts = [create_post(novelty_score=0.8) for _ in range(5)]
    energy = calculator.calculate_energy(posts)
    assert energy > 0.6

# Test trigger rules
def test_relevance_trigger():
    posts = [create_post(content="The mechanism involves receptor binding")]
    biology_agent = create_agent(domain_keywords=["mechanism", "receptor"])
    should_respond, _ = biology_agent.should_respond(posts, Phase.EXPLORE)
    assert should_respond

# Test phase detection
def test_debate_phase_detection():
    posts = [
        create_post(stance=AgentStance.CRITICAL, citations=[...]),
        create_post(stance=AgentStance.CRITICAL, citations=[...]),
        create_post(stance=AgentStance.SUPPORTIVE, citations=[...]),
    ]
    phase = observer.detect_phase(posts)
    assert phase.current_phase == Phase.DEBATE
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_full_deliberation():
    engine = create_engine()
    session = create_session(hypothesis="GLP-1 agonists improve cognitive function")

    posts = []
    async for item in engine.run_deliberation(session, session.hypothesis):
        if isinstance(item, Post):
            posts.append(item)

    assert len(posts) >= 12  # Minimum depth
    assert any(p.stance == AgentStance.CRITICAL for p in posts)
    assert any(p.novelty_score > 0.5 for p in posts)
```

### Behavioral Tests

```python
def test_red_team_prevents_premature_consensus():
    """Red Team should respond when consensus forms."""
    posts = [
        create_post(agent_id="biology", stance=AgentStance.SUPPORTIVE),
        create_post(agent_id="chemistry", stance=AgentStance.SUPPORTIVE),
        create_post(agent_id="clinical", stance=AgentStance.SUPPORTIVE),
    ]
    red_team = create_red_team_agent()
    should_respond, rules = red_team.should_respond(posts, Phase.DEBATE)
    assert should_respond
    assert "consensus_forming" in rules
```

---

## Deployment

### Docker Compose

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/colloquium
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      - db

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend

  db:
    image: pgvector/pgvector:pg16
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=colloquium

volumes:
  postgres_data:
```

---

*Document created: 2026-02-10*
*Emergent Deliberation System v1.0*
