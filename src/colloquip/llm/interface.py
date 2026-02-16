"""LLM interface protocol for the deliberation system."""

from typing import List, Optional, Protocol, runtime_checkable

from colloquip.models import AgentStance


@runtime_checkable
class LLMResponse(Protocol):
    """Structured response from an LLM call."""

    content: str
    stance: AgentStance
    key_claims: List[str]
    questions_raised: List[str]
    connections_identified: List[str]
    novelty_score: float


class LLMResult:
    """Concrete implementation of LLM response."""

    def __init__(
        self,
        content: str,
        stance: AgentStance,
        key_claims: Optional[List[str]] = None,
        questions_raised: Optional[List[str]] = None,
        connections_identified: Optional[List[str]] = None,
        novelty_score: float = 0.5,
        input_tokens: int = 0,
        output_tokens: int = 0,
        citations: Optional[List[dict]] = None,
    ):
        self.content = content
        self.stance = stance
        self.key_claims = key_claims or []
        self.questions_raised = questions_raised or []
        self.connections_identified = connections_identified or []
        self.novelty_score = novelty_score
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.citations = citations or []


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
