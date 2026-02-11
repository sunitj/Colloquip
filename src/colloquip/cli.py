"""CLI runner for Colloquip deliberation system."""

import argparse
import asyncio
import json
import sys
from typing import Dict, Optional, Union

from colloquip.agents.base import BaseDeliberationAgent
from colloquip.config import EnergyConfig, ObserverConfig
from colloquip.display import create_display
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


def _create_llm(mode: str, seed: int = 42, model: Optional[str] = None):
    """Create the appropriate LLM backend."""
    if mode == "mock":
        return MockLLM(behavior=MockBehavior.MIXED, seed=seed)

    from colloquip.llm.anthropic import AnthropicLLM
    return AnthropicLLM(model=model or "claude-sonnet-4-5-20250929")


async def run_deliberation(
    hypothesis: str,
    mode: str = "mock",
    seed: int = 42,
    model: Optional[str] = None,
    max_turns: int = 30,
    save_transcript: Optional[str] = None,
    use_rich: bool = True,
) -> None:
    """Run a complete deliberation and display results."""
    llm = _create_llm(mode, seed=seed, model=model)
    agents = create_default_agents(llm)
    num_agents = len(agents)

    energy_config = EnergyConfig()
    energy_calc = EnergyCalculator(config=energy_config)
    observer = ObserverAgent(energy_calculator=energy_calc, num_agents=num_agents)

    engine = EmergentDeliberationEngine(
        agents=agents,
        observer=observer,
        energy_calculator=energy_calc,
        llm=llm,
        max_turns=max_turns,
        min_posts=12,
    )

    session = DeliberationSession(hypothesis=hypothesis)
    display = create_display(use_rich=use_rich)
    display.show_header(hypothesis)

    post_count = 0
    transcript = []

    async for event in engine.run_deliberation(session, hypothesis):
        if isinstance(event, Post):
            post_count += 1
            display.show_post(event)
            if save_transcript is not None:
                transcript.append({
                    "type": "post",
                    "agent_id": event.agent_id,
                    "content": event.content,
                    "stance": event.stance.value,
                    "novelty_score": event.novelty_score,
                    "phase": event.phase.value,
                    "triggered_by": event.triggered_by,
                })

        elif isinstance(event, PhaseSignal):
            display.show_phase_transition(event)

        elif isinstance(event, EnergyUpdate):
            display.show_energy(event)

        elif isinstance(event, ConsensusMap):
            display.show_consensus(event)
            if save_transcript is not None:
                transcript.append({
                    "type": "consensus",
                    "summary": event.summary,
                    "agreements": event.agreements,
                    "disagreements": event.disagreements,
                    "minority_positions": event.minority_positions,
                    "final_stances": {k: v.value for k, v in event.final_stances.items()},
                })

    # Token usage (only for real mode)
    token_usage = None
    if hasattr(llm, "token_usage"):
        token_usage = llm.token_usage

    display.show_footer(post_count, token_usage)

    # Save transcript if requested
    if save_transcript:
        with open(save_transcript, "w") as f:
            json.dump(transcript, f, indent=2)
        print(f"\nTranscript saved to: {save_transcript}")


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
        "--model",
        type=str,
        default=None,
        help="Claude model to use in real mode (default: claude-sonnet-4-5-20250929)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for mock mode (for reproducibility)",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=30,
        help="Maximum deliberation turns",
    )
    parser.add_argument(
        "--save-transcript",
        type=str,
        default=None,
        help="Save deliberation transcript to JSON file",
    )
    parser.add_argument(
        "--no-rich",
        action="store_true",
        help="Disable rich terminal output",
    )
    args = parser.parse_args()

    asyncio.run(run_deliberation(
        hypothesis=args.hypothesis,
        mode=args.mode,
        seed=args.seed,
        model=args.model,
        max_turns=args.max_turns,
        save_transcript=args.save_transcript,
        use_rich=not args.no_rich,
    ))


if __name__ == "__main__":
    main()
