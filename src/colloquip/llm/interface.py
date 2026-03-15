"""LLM interface protocol for the deliberation system."""

from typing import Any, Callable, Coroutine, Dict, List, Optional, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from colloquip.models import AgentStance


class ToolInvocation(BaseModel):
    """Record of a tool call made during LLM generation."""

    tool_name: str
    tool_input: Dict[str, Any] = Field(default_factory=dict)
    tool_result: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: float = 0.0


# Type alias for the async callable that executes tool calls
ToolExecutor = Callable[[str, Dict[str, Any]], Coroutine[Any, Any, Dict[str, Any]]]


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
        tool_invocations: Optional[List[ToolInvocation]] = None,
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
        self.tool_invocations = tool_invocations or []


@runtime_checkable
class LLMInterface(Protocol):
    """Protocol for LLM backends (real or mock)."""

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_executor: Optional[ToolExecutor] = None,
    ) -> LLMResult:
        """Generate a structured response from the LLM.

        Args:
            system_prompt: System prompt for the LLM.
            user_prompt: User prompt for the LLM.
            max_tokens: Maximum tokens to generate.
            tools: List of Claude API tool schemas.
            tool_executor: Async callable to execute tool calls.
                           Signature: (tool_name, tool_input) -> result_dict
        """
        ...

    async def generate_synthesis(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate a free-form synthesis response."""
        ...
