# Colloquip

An emergent deliberation system where multi-agent scientific discussion arises from simple local rules rather than engineered orchestration.

**Status**: Pre-implementation (design complete, building foundation)

## Overview

Colloquip is a multi-agent platform for scientific hypothesis deliberation. Six specialist agents (Biology, Chemistry, ADMET, Clinical, Regulatory, Red Team) plus one Observer agent engage in emergent conversation driven by:

- **Trigger-based self-selection** — agents speak when they have something to contribute
- **Observer-detected phases** — EXPLORE, DEBATE, DEEPEN, CONVERGE, SYNTHESIS
- **Energy-based termination** — conversations end naturally when ideas are exhausted

## Documentation

| Document | Description |
|----------|-------------|
| [Implementation Plan](plan/IMPLEMENTATION_PLAN.md) | Phased build plan with testing and success criteria |
| [Design Specification](docs/README.md) | System overview and document index |
| [System Design](docs/SYSTEM_DESIGN.md) | Architecture, data models, API, data flow |
| [Energy Model](docs/ENERGY_MODEL.md) | Energy calculation and termination logic |
| [Observer Spec](docs/OBSERVER_SPEC.md) | Phase detection, hysteresis, meta-observations |
| [Agent Prompts](docs/AGENT_PROMPTS.md) | All agent personas and phase mandates |
| [Trigger Rules](docs/TRIGGER_RULES.md) | Agent self-selection trigger rules |

## Getting Started

See the [Implementation Plan](plan/IMPLEMENTATION_PLAN.md) for build order and success criteria.
