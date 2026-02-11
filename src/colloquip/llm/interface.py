"""LLM interface protocol for the deliberation system."""

from typing import Protocol, runtime_checkable

from colloquip.models import AgentStance


@runtime_checkable
class LLMResponse(Protocol):
    """Structured response from an LLM call."""
    content: str
    stance: AgentStance
    key_claims: list[str]
    questions_raised: list[str]
    connections_identified: list[str]
    novelty_score: float


class LLMResult:
    """Concrete implementation of LLM response."""

    def __init__(
        self,
        content: str,
        stance: AgentStance,
        key_claims: list[str] | None = None,
        questions_raised: list[str] | None = None,
        connections_identified: list[str] | None = None,
        novelty_score: float = 0.5,
    ):
        self.content = content
        self.stance = stance
        self.key_claims = key_claims or []
        self.questions_raised = questions_raised or []
        self.connections_identified = connections_identified or []
        self.novelty_score = novelty_score


@runtime_checkable
class LLMInterface(Protocol):
    """Protocol for LLM backends (real or mock)."""

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMResult:
        """Generate a structured response from the LLM."""
        ...

    async def generate_synthesis(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Generate a free-form synthesis response."""
        ...
