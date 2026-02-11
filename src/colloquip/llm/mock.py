"""Mock LLM for testing without API calls."""

import random
from enum import Enum
from typing import List, Optional

from colloquip.llm.interface import LLMInterface, LLMResult
from colloquip.models import AgentStance


class MockBehavior(str, Enum):
    MIXED = "mixed"
    ALWAYS_SUPPORTIVE = "always_supportive"
    ALWAYS_CRITICAL = "always_critical"
    HIGH_NOVELTY = "high_novelty"
    LOW_NOVELTY = "low_novelty"
    DECLINING = "declining"


class MockLLM:
    """Mock LLM that returns deterministic, configurable responses."""

    def __init__(
        self,
        behavior: MockBehavior = MockBehavior.MIXED,
        seed: Optional[int] = None,
    ):
        self.behavior = behavior
        self.rng = random.Random(seed)
        self._call_count = 0

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMResult:
        self._call_count += 1
        stance = self._pick_stance()
        novelty = self._pick_novelty()

        # Extract agent identity from system prompt for varied content
        agent_name = self._extract_agent_name(system_prompt)
        phase = self._extract_phase(system_prompt)

        content = self._generate_content(agent_name, phase, stance)
        claims = self._generate_claims(agent_name, stance)
        questions = self._generate_questions(agent_name)
        connections = self._generate_connections(agent_name, novelty)

        return LLMResult(
            content=content,
            stance=stance,
            key_claims=claims,
            questions_raised=questions,
            connections_identified=connections,
            novelty_score=novelty,
        )

    async def generate_synthesis(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        return (
            "After thorough deliberation, the panel has reached a nuanced consensus. "
            "The hypothesis shows promise but requires further validation. "
            "Key areas of agreement include the mechanistic plausibility and "
            "the need for additional preclinical evidence. "
            "The Red Team raised important concerns about translational gaps "
            "that should be addressed in future studies."
        )

    def _pick_stance(self) -> AgentStance:
        if self.behavior == MockBehavior.ALWAYS_SUPPORTIVE:
            return AgentStance.SUPPORTIVE
        if self.behavior == MockBehavior.ALWAYS_CRITICAL:
            return AgentStance.CRITICAL
        stances = [
            AgentStance.SUPPORTIVE,
            AgentStance.CRITICAL,
            AgentStance.NEUTRAL,
            AgentStance.NOVEL_CONNECTION,
        ]
        weights = [0.35, 0.30, 0.25, 0.10]
        return self.rng.choices(stances, weights=weights, k=1)[0]

    def _pick_novelty(self) -> float:
        if self.behavior == MockBehavior.HIGH_NOVELTY:
            return round(self.rng.uniform(0.6, 0.95), 2)
        if self.behavior == MockBehavior.LOW_NOVELTY:
            return round(self.rng.uniform(0.05, 0.3), 2)
        if self.behavior == MockBehavior.DECLINING:
            base = max(0.1, 0.9 - self._call_count * 0.05)
            return round(self.rng.uniform(base * 0.8, base), 2)
        return round(self.rng.uniform(0.2, 0.8), 2)

    def _extract_agent_name(self, system_prompt: str) -> str:
        for name in ["Biology", "Chemistry", "ADMET", "Clinical", "Regulatory", "Red Team"]:
            if name.lower() in system_prompt.lower():
                return name
        return "Agent"

    def _extract_phase(self, system_prompt: str) -> str:
        for phase in ["EXPLORATION", "DEBATE", "DEEPENING", "CONVERGENCE"]:
            if phase in system_prompt:
                return phase
        return "EXPLORATION"

    def _generate_content(self, agent: str, phase: str, stance: AgentStance) -> str:
        templates = {
            AgentStance.SUPPORTIVE: (
                f"From the {agent} perspective, the evidence supports this hypothesis. "
                f"The mechanistic data aligns with known pathway biology, and "
                f"preclinical models show consistent results. "
                f"What are the key biomarkers we should track?"
            ),
            AgentStance.CRITICAL: (
                f"As the {agent} expert, I must challenge this assumption. "
                f"The data clearly shows limitations that others have overlooked. "
                f"Previous programs targeting this pathway have failed, and "
                f"the safety margin remains uncertain."
            ),
            AgentStance.NEUTRAL: (
                f"The {agent} analysis reveals mixed evidence. "
                f"While some preclinical data is encouraging, the translational "
                f"gap remains significant. Further investigation of the target "
                f"selectivity profile could be informative."
            ),
            AgentStance.NOVEL_CONNECTION: (
                f"Interestingly, the {agent} data suggests an unexpected connection. "
                f"The pathway mechanism discussed by other panelists could "
                f"explain the clinical observation through a safety-efficacy bridge. "
                f"This cross-domain insight warrants deeper exploration."
            ),
        }
        return templates.get(stance, templates[AgentStance.NEUTRAL])

    def _generate_claims(self, agent: str, stance: AgentStance) -> List[str]:
        base_claims = [
            f"The {agent.lower()} evidence supports further investigation",
            f"Key {agent.lower()} parameters fall within acceptable ranges",
        ]
        if stance == AgentStance.CRITICAL:
            base_claims.append(f"The {agent.lower()} risk profile requires attention")
        return base_claims

    def _generate_questions(self, agent: str) -> List[str]:
        return [
            f"What is the expected therapeutic index based on {agent.lower()} data?",
            f"Have similar {agent.lower()} patterns been observed in related programs?",
        ]

    def _generate_connections(self, agent: str, novelty: float) -> List[str]:
        if novelty > 0.6:
            return [f"Cross-domain link between {agent.lower()} and clinical endpoints"]
        return []
