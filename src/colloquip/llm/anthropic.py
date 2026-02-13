"""Anthropic Claude adapter for the deliberation system."""

import logging
import re
from typing import List, Optional

from colloquip.llm.interface import LLMResult
from colloquip.models import AgentStance

logger = logging.getLogger(__name__)

# Structured output extraction patterns
_STANCE_PATTERN = re.compile(
    r"\*?\*?Stance\*?\*?[:\s]*(SUPPORTIVE|CRITICAL|NEUTRAL|NOVEL_CONNECTION)",
    re.IGNORECASE,
)
_LIST_ITEM = r"(?:\s*(?:[-*]|\d+[.)])\s+.+\n?)+"
_CLAIMS_PATTERN = re.compile(
    r"\*?\*?Key Claims\*?\*?[:\s]*\n(" + _LIST_ITEM + ")",
    re.IGNORECASE,
)
_QUESTIONS_PATTERN = re.compile(
    r"\*?\*?Questions Raised\*?\*?[:\s]*\n(" + _LIST_ITEM + ")",
    re.IGNORECASE,
)
_CONNECTIONS_PATTERN = re.compile(
    r"\*?\*?Connections Identified\*?\*?[:\s]*\n(" + _LIST_ITEM + ")",
    re.IGNORECASE,
)

_STANCE_MAP = {
    "supportive": AgentStance.SUPPORTIVE,
    "critical": AgentStance.CRITICAL,
    "neutral": AgentStance.NEUTRAL,
    "novel_connection": AgentStance.NOVEL_CONNECTION,
}


def _extract_list_items(text: str) -> List[str]:
    """Extract list items from bullet or numbered list formats."""
    items = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if line.startswith(("-", "*")):
            item = line.lstrip("-* ").strip()
            if item:
                items.append(item)
        elif re.match(r"^\d+[.)]\s+", line):
            item = re.sub(r"^\d+[.)]\s+", "", line).strip()
            if item:
                items.append(item)
    return items


def parse_agent_response(raw_text: str) -> LLMResult:
    """Parse a structured agent response from Claude's output.

    Extracts stance, key claims, questions, connections, and novelty
    from the markdown-formatted response.
    """
    # Extract stance
    stance = AgentStance.NEUTRAL
    stance_match = _STANCE_PATTERN.search(raw_text)
    if stance_match:
        stance_str = stance_match.group(1).lower()
        stance = _STANCE_MAP.get(stance_str, AgentStance.NEUTRAL)

    # Extract claims
    claims: List[str] = []
    claims_match = _CLAIMS_PATTERN.search(raw_text)
    if claims_match:
        claims = _extract_list_items(claims_match.group(1))

    # Extract questions
    questions: List[str] = []
    questions_match = _QUESTIONS_PATTERN.search(raw_text)
    if questions_match:
        questions = _extract_list_items(questions_match.group(1))

    # Extract connections
    connections: List[str] = []
    connections_match = _CONNECTIONS_PATTERN.search(raw_text)
    if connections_match:
        connections = _extract_list_items(connections_match.group(1))

    # Estimate novelty: novel_connection stance or explicit connections → higher novelty
    novelty = 0.5
    if stance == AgentStance.NOVEL_CONNECTION:
        novelty = 0.8
    elif connections:
        novelty = 0.7
    elif stance == AgentStance.CRITICAL:
        novelty = 0.6

    # Strip the structured sections from content to get the main analysis
    content = raw_text.strip()

    return LLMResult(
        content=content,
        stance=stance,
        key_claims=claims[:5],
        questions_raised=questions[:3],
        connections_identified=connections[:5],
        novelty_score=novelty,
    )


class AnthropicLLM:
    """Anthropic Claude adapter implementing the LLM interface.

    Requires the `anthropic` optional dependency:
        pip install colloquip[llm]
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-5-20250929",
        max_tokens: int = 1024,
        temperature: float = 0.7,
        api_key: Optional[str] = None,
        max_retries: int = 3,
    ):
        try:
            import anthropic
        except ImportError:
            raise ImportError(
                "The 'anthropic' package is required for real LLM mode. "
                "Install it with: pip install colloquip[llm]"
            )

        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.max_retries = max_retries
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._call_count = 0

        self.client = anthropic.AsyncAnthropic(api_key=api_key, max_retries=max_retries)

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMResult:
        """Generate a structured agent response via Claude."""
        self._call_count += 1

        message = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        # Track token usage
        self._total_input_tokens += message.usage.input_tokens
        self._total_output_tokens += message.usage.output_tokens

        if not message.content:
            raise ValueError("LLM returned empty content (possibly filtered or rate-limited)")
        raw_text = message.content[0].text
        return parse_agent_response(raw_text)

    async def generate_synthesis(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Generate a free-form synthesis response via Claude."""
        self._call_count += 1

        message = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens * 2,  # Synthesis needs more space
            temperature=0.5,  # Lower temperature for synthesis
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        self._total_input_tokens += message.usage.input_tokens
        self._total_output_tokens += message.usage.output_tokens

        if not message.content:
            raise ValueError("LLM returned empty synthesis content")
        return message.content[0].text

    @property
    def token_usage(self) -> dict:
        """Return cumulative token usage stats."""
        return {
            "input_tokens": self._total_input_tokens,
            "output_tokens": self._total_output_tokens,
            "total_tokens": self._total_input_tokens + self._total_output_tokens,
            "calls": self._call_count,
        }
