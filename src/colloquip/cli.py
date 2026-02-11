"""CLI runner for Colloquip deliberation system."""

import argparse
import asyncio
import sys
from typing import Dict

from colloquip.agents.base import BaseDeliberationAgent
from colloquip.config import ColloquipConfig, EnergyConfig, ObserverConfig
from colloquip.energy import EnergyCalculator
from colloquip.engine import EmergentDeliberationEngine
from colloquip.llm.mock import MockBehavior, MockLLM
from colloquip.models import (
    AgentConfig,
    ConsensusMap,
    DeliberationSession,
    EnergyUpdate,
    Phase,
    PhaseSignal,
    Post,
)
from colloquip.observer import ObserverAgent


# Default agent configurations for the drug discovery domain
DEFAULT_AGENTS: Dict[str, dict] = {
    "biology": {
        "display_name": "Biology & Target ID",
        "domain_keywords": [
            "mechanism", "target", "pathway", "receptor", "gene",
            "protein", "cell", "tissue", "expression", "knockout",
        ],
        "knowledge_scope": ["biology", "preclinical"],
        "is_red_team": False,
    },
    "chemistry": {
        "display_name": "Discovery Chemistry",
        "domain_keywords": [
            "synthesis", "compound", "molecule", "SAR", "analog",
            "scaffold", "reaction", "binding", "selectivity", "potency",
        ],
        "knowledge_scope": ["chemistry", "manufacturing"],
        "is_red_team": False,
    },
    "admet": {
        "display_name": "ADMET & Toxicology",
        "domain_keywords": [
            "toxicity", "safety", "metabolism", "clearance", "half-life",
            "bioavailability", "CYP", "hERG", "genotoxicity", "therapeutic index",
        ],
        "knowledge_scope": ["safety", "preclinical"],
        "is_red_team": False,
    },
    "clinical": {
        "display_name": "Clinical Translation",
        "domain_keywords": [
            "patient", "trial", "endpoint", "efficacy", "dose",
            "population", "outcome", "standard of care", "indication", "biomarker",
        ],
        "knowledge_scope": ["clinical", "regulatory"],
        "is_red_team": False,
    },
    "regulatory": {
        "display_name": "Regulatory Strategy",
        "domain_keywords": [
            "FDA", "EMA", "approval", "guidance", "precedent",
            "pathway", "label", "IND", "NDA", "breakthrough",
        ],
        "knowledge_scope": ["regulatory", "clinical"],
        "is_red_team": False,
    },
    "redteam": {
        "display_name": "Red Team (Adversarial)",
        "domain_keywords": [
            "assumption", "bias", "alternative", "failure", "risk",
            "overlooked", "counter", "dissent", "minority", "challenge",
        ],
        "knowledge_scope": [
            "biology", "chemistry", "safety", "clinical", "regulatory",
        ],
        "is_red_team": True,
    },
}

# Minimal persona prompts for mock mode
MINIMAL_PERSONAS: Dict[str, str] = {
    "biology": (
        "You are the Biology & Target Identification expert. "
        "You evaluate hypotheses through biological plausibility and mechanistic coherence."
    ),
    "chemistry": (
        "You are the Discovery Chemistry expert. "
        "You evaluate hypotheses through chemical tractability and synthetic accessibility."
    ),
    "admet": (
        "You are the ADMET & Toxicology expert. "
        "You evaluate hypotheses through drug safety and therapeutic index."
    ),
    "clinical": (
        "You are the Clinical Translation expert. "
        "You evaluate hypotheses through patient relevance and translational validity."
    ),
    "regulatory": (
        "You are the Regulatory Strategy expert. "
        "You evaluate hypotheses through regulatory precedent and approval pathways."
    ),
    "redteam": (
        "You are the Red Team adversarial expert. "
        "You challenge assumptions, surface uncomfortable truths, and prevent premature consensus."
    ),
}


def create_default_agents(llm) -> Dict[str, BaseDeliberationAgent]:
    """Create the default set of 6 agents with minimal personas."""
    agents = {}
    for agent_id, agent_data in DEFAULT_AGENTS.items():
        config = AgentConfig(
            agent_id=agent_id,
            display_name=agent_data["display_name"],
            persona_prompt=MINIMAL_PERSONAS[agent_id],
            phase_mandates={},  # Will use defaults from prompts.py
            domain_keywords=agent_data["domain_keywords"],
            knowledge_scope=agent_data["knowledge_scope"],
            is_red_team=agent_data["is_red_team"],
        )
        agents[agent_id] = BaseDeliberationAgent(config=config, llm=llm)
    return agents


async def run_mock_deliberation(hypothesis: str, seed: int = 42) -> None:
    """Run a complete mock deliberation and print results."""
    llm = MockLLM(behavior=MockBehavior.MIXED, seed=seed)
    agents = create_default_agents(llm)

    energy_config = EnergyConfig()
    energy_calc = EnergyCalculator(config=energy_config)
    observer = ObserverAgent(energy_calculator=energy_calc)

    engine = EmergentDeliberationEngine(
        agents=agents,
        observer=observer,
        energy_calculator=energy_calc,
        llm=llm,
        max_turns=30,
        min_posts=12,
    )

    session = DeliberationSession(hypothesis=hypothesis)

    print(f"\n{'='*70}")
    print(f"COLLOQUIP — Emergent Deliberation")
    print(f"{'='*70}")
    print(f"Hypothesis: {hypothesis}")
    print(f"{'='*70}\n")

    post_count = 0
    current_phase = Phase.EXPLORE

    async for event in engine.run_deliberation(session, hypothesis):
        if isinstance(event, Post):
            post_count += 1
            phase_label = event.phase.value.upper()
            stance_label = event.stance.value.upper()
            agent_label = event.agent_id.upper()
            triggers = ", ".join(event.triggered_by) if event.triggered_by else "seed"

            print(f"[{post_count:02d}] {agent_label} | {phase_label} | {stance_label}")
            print(f"     Triggers: {triggers}")
            print(f"     Novelty: {event.novelty_score:.2f}")
            # Truncate content for display
            content = event.content[:200] + "..." if len(event.content) > 200 else event.content
            print(f"     {content}")
            print()

        elif isinstance(event, PhaseSignal):
            if event.current_phase != current_phase:
                current_phase = event.current_phase
                print(f"  >>> PHASE TRANSITION: {current_phase.value.upper()} "
                      f"(confidence: {event.confidence:.2f})")
                if event.observation:
                    print(f"  >>> Observer: {event.observation}")
                print()

        elif isinstance(event, EnergyUpdate):
            bar_len = int(event.energy * 20)
            bar = "#" * bar_len + "." * (20 - bar_len)
            print(f"  Energy [{bar}] {event.energy:.3f}")
            print()

        elif isinstance(event, ConsensusMap):
            print(f"\n{'='*70}")
            print("SYNTHESIS — Consensus Map")
            print(f"{'='*70}")
            print(f"\nSummary: {event.summary}\n")
            if event.agreements:
                print("Agreements:")
                for a in event.agreements:
                    print(f"  + {a}")
            if event.disagreements:
                print("\nDisagreements:")
                for d in event.disagreements:
                    print(f"  - {d}")
            if event.minority_positions:
                print("\nMinority Positions:")
                for m in event.minority_positions:
                    print(f"  ? {m}")
            print(f"\nFinal Stances: {event.final_stances}")
            print(f"\n{'='*70}")

    print(f"\nDeliberation complete: {post_count} posts generated.")


def main():
    parser = argparse.ArgumentParser(
        description="Colloquip: Emergent multi-agent deliberation"
    )
    parser.add_argument(
        "--hypothesis", "-H",
        type=str,
        default="GLP-1 agonists may improve cognitive function in Alzheimer's patients",
        help="The hypothesis to deliberate",
    )
    parser.add_argument(
        "--mode",
        choices=["mock", "real"],
        default="mock",
        help="LLM mode: mock (no API calls) or real (requires ANTHROPIC_API_KEY)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for mock mode (for reproducibility)",
    )
    args = parser.parse_args()

    if args.mode == "real":
        print("Real LLM mode not yet implemented. Use --mode mock.", file=sys.stderr)
        sys.exit(1)

    asyncio.run(run_mock_deliberation(args.hypothesis, seed=args.seed))


if __name__ == "__main__":
    main()
