# Emergent Deliberation System

A complex-systems approach to multi-agent scientific deliberation, where serendipity and insight emerge from simple local rules rather than engineered detection algorithms.

---

## Design Philosophy

Inspired by cellular automata (Conway's Game of Life) and flocking behavior:

- **Simple local rules** → **Complex global patterns**
- **No central orchestrator** → **Emergent coordination**
- **Authentic serendipity** → Not detected, but naturally arising

---

## Document Index

| Document | Purpose |
|----------|---------|
| [AGENT_PROMPTS.md](./AGENT_PROMPTS.md) | Complete prompts for all 6 scientist agents + observer, including phase-dependent mandates |
| [OBSERVER_SPEC.md](./OBSERVER_SPEC.md) | Observer agent specification: phase detection, hysteresis, meta-observations |
| [TRIGGER_RULES.md](./TRIGGER_RULES.md) | Detailed trigger rule definitions for agent self-selection |
| [ENERGY_MODEL.md](./ENERGY_MODEL.md) | Energy calculation and termination logic |
| [SYSTEM_DESIGN.md](./SYSTEM_DESIGN.md) | Complete architecture, data flow, API design |

---

## Quick Reference

### The Agents

| Agent | Role | Key Trait |
|-------|------|-----------|
| **Biology** | Target validation, mechanism | Hypothesis-driven, builds from first principles |
| **Chemistry** | Tractability, synthesis | Pragmatic, solution-oriented |
| **ADMET** | Safety, toxicology | Risk-averse, finds reasons things won't work |
| **Clinical** | Patient relevance, translation | Patient-centric, bridges bench to bedside |
| **Regulatory** | Precedent, pathways | Cautious, precedent-driven |
| **Red Team** | Adversarial challenge | Contrarian, prevents premature consensus |
| **Observer** | Phase detection | Meta-cognitive, doesn't participate in content |

### The Phases

| Phase | Behavior | Detection Signal |
|-------|----------|------------------|
| **EXPLORE** | Speculative, questioning | High question rate, diverse participation |
| **DEBATE** | Evidence-heavy, challenging | High disagreement, lots of citations |
| **DEEPEN** | Focused, drilling down | Low diversity, high novelty |
| **CONVERGE** | Synthesizing, concluding | Low energy, stagnating |
| **SYNTHESIS** | Final summary | Explicit (not detected) |

### The Trigger Rules

| Rule | Fires When |
|------|------------|
| **Relevance** | My domain mentioned in recent posts |
| **Disagreement** | Strong claim made in my domain |
| **Question** | Unanswered question in my domain |
| **Silence Breaking** | Haven't spoken in a while, still relevant |
| **Bridge Opportunity** | I can connect concepts from other agents |
| **Uncertainty Response** | I have evidence for others' uncertainty |

### Energy Formula

```
Energy = 0.4 × Novelty + 0.3 × Disagreement + 0.2 × Questions - 0.1 × Staleness
```

Terminate when energy < 0.2 for 3 consecutive turns.

---

## Key Differences from Classic Colloquium

| Aspect | Classic | Emergent |
|--------|---------|----------|
| Phase control | Hardcoded sequence | Observer detects from dynamics |
| Agent triggering | Engine calls all agents | Agents self-select via rules |
| Termination | Fixed round count | Energy-based decay |
| Agent prompts | Static persona | Persona + phase mandate |
| Serendipity | Keyword detection | Emerges from interactions |

---

## Getting Started

### 1. Read the Design Documents

Start with [SYSTEM_DESIGN.md](./SYSTEM_DESIGN.md) for architecture overview, then dive into specific components.

### 2. Understand the Prompts

[AGENT_PROMPTS.md](./AGENT_PROMPTS.md) contains the complete prompts. Each agent has:
- Core persona (~2000-4000 tokens)
- Phase mandates (4 phases × ~100 tokens each)
- Response guidelines

### 3. Implement Components

Suggested order:
1. Data models (Phase, ConversationMetrics, etc.)
2. Energy calculator
3. Observer agent
4. Trigger evaluator
5. Base agent with `should_respond()`
6. Main deliberation loop
7. API endpoints

### 4. Test Incrementally

- Unit test each component in isolation
- Integration test the full loop
- Behavioral tests for emergent properties

---

## Configuration Defaults

```yaml
engine:
  max_turns: 30
  min_posts: 12

observer:
  hysteresis_threshold: 3
  window_size: 10

energy:
  threshold: 0.2
  low_energy_rounds: 3

triggers:
  refractory_period: 2
  relevance_threshold: 2
  silence_max: 6
```

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Agent trigger accuracy | >80% valuable posts |
| Phase detection accuracy | >70% human agreement |
| Serendipity emergence | Novel connections without forcing |
| Conversation naturalness | Reduced repetition vs. classic |
| Energy termination | Synthesis at appropriate time |

---

## Related Documents

- [../VISION_ANALYSIS.md](../VISION_ANALYSIS.md) — Vision and gap analysis
- [../IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) — Implementation roadmap

---

*Emergent Deliberation System v1.0*
*Created: 2026-02-10*
