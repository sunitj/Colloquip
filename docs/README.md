# Design Specifications

Technical implementation specs for the Colloquium emergent deliberation engine. These documents contain complete algorithm implementations, component interfaces, and tuning guidance.

For user-facing documentation, platform features, API reference, and development guides, see the **[Wiki](https://github.com/sunitj/Colloquip/wiki)**.

---

## Documents

| Document | Contents | Wiki Counterpart |
|----------|----------|-----------------|
| [SYSTEM_DESIGN.md](./SYSTEM_DESIGN.md) | Architecture diagram, component interfaces, Pydantic models, error handling, deployment | [Architecture Overview](https://github.com/sunitj/Colloquip/wiki/Architecture-Overview) |
| [ENERGY_MODEL.md](./ENERGY_MODEL.md) | Energy calculation functions, termination state machine, injection logic, calibration guidelines | [Core Concepts](https://github.com/sunitj/Colloquip/wiki/Core-Concepts) |
| [OBSERVER_SPEC.md](./OBSERVER_SPEC.md) | Metric calculations, phase detection algorithm, hysteresis, confidence, edge cases | [Core Concepts](https://github.com/sunitj/Colloquip/wiki/Core-Concepts) |
| [TRIGGER_RULES.md](./TRIGGER_RULES.md) | All 9 trigger rule implementations, phase modulation tables, refractory period, design philosophy | [Core Concepts](https://github.com/sunitj/Colloquip/wiki/Core-Concepts) |
| [AGENT_PROMPTS.md](./AGENT_PROMPTS.md) | Complete persona prompts for all agents, phase mandates, response guidelines | [Agent System](https://github.com/sunitj/Colloquip/wiki/Agent-System) |

## Design Philosophy

Inspired by cellular automata (Conway's Game of Life) and flocking behavior:

- **Simple local rules** → **Complex global patterns**
- **No central orchestrator** → **Emergent coordination**
- **Authentic serendipity** → Not detected, but naturally arising

## Relationship to Wiki

These docs serve as **implementation reference** -- they contain working code, algorithm pseudocode, and calibration data that complement the wiki's higher-level explanations. The wiki is the canonical source for:

- Platform features (communities, watchers, memory, notifications)
- API reference (33+ endpoints)
- Frontend architecture
- Database schema
- Development workflow
- Getting started guide
