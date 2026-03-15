"""Anthropic Claude adapter for the deliberation system."""

import logging
import re
import time
from typing import Any, Dict, List, Optional

from colloquip.llm.interface import LLMResult, ToolExecutor, ToolInvocation
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
    content = raw_text
    for pattern in [_STANCE_PATTERN, _CLAIMS_PATTERN, _QUESTIONS_PATTERN, _CONNECTIONS_PATTERN]:
        # Remove entire matched section (header + list items)
        content = pattern.sub("", content)
    # Also remove standalone section headers that may remain
    content = re.sub(
        r"^#{1,4}\s*(Analysis|Stance|Key Claims|Questions Raised|Connections Identified)\s*$",
        "",
        content,
        flags=re.MULTILINE | re.IGNORECASE,
    )
    content = re.sub(r"\n{3,}", "\n\n", content).strip()

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
        model: str = "claude-opus-4-6",
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
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_executor: Optional[ToolExecutor] = None,
    ) -> LLMResult:
        """Generate a structured agent response via Claude.

        When tools are provided, handles the tool_use loop: if Claude responds
        with tool_use blocks, executes them via tool_executor and feeds results
        back until a final text response is produced.
        """
        self._call_count += 1

        messages: List[Dict[str, Any]] = [{"role": "user", "content": user_prompt}]
        total_input = 0
        total_output = 0
        tool_invocations: List[ToolInvocation] = []
        max_tool_rounds = 10  # Safety limit

        for _round in range(max_tool_rounds):
            kwargs: Dict[str, Any] = {
                "model": self.model,
                "max_tokens": max_tokens or self.max_tokens,
                "temperature": self.temperature,
                "system": system_prompt,
                "messages": messages,
            }
            if tools:
                kwargs["tools"] = tools

            message = await self.client.messages.create(**kwargs)

            total_input += message.usage.input_tokens
            total_output += message.usage.output_tokens

            if not message.content:
                raise ValueError("LLM returned empty content (possibly filtered or rate-limited)")

            # Check for tool_use blocks
            tool_use_blocks = [b for b in message.content if getattr(b, "type", None) == "tool_use"]

            if not tool_use_blocks or not tool_executor:
                # Final response — extract text and return
                text_parts = [b.text for b in message.content if getattr(b, "type", None) == "text"]
                raw_text = "\n".join(text_parts) if text_parts else ""
                if not raw_text:
                    raise ValueError("LLM returned no text content in final response")

                self._total_input_tokens += total_input
                self._total_output_tokens += total_output

                result = parse_agent_response(raw_text)
                result.input_tokens = total_input
                result.output_tokens = total_output
                result.tool_invocations = tool_invocations
                return result

            # Execute tool calls and build follow-up messages
            # Add assistant message with all content blocks
            messages.append({"role": "assistant", "content": message.content})

            tool_results_content = []
            for block in tool_use_blocks:
                tool_name = block.name
                tool_input = block.input
                tool_id = block.id

                start_time = time.monotonic()
                try:
                    tool_result = await tool_executor(tool_name, tool_input)
                except Exception as e:
                    logger.error("Tool execution failed for %s: %s", tool_name, e)
                    tool_result = {"error": str(e)}
                elapsed_ms = (time.monotonic() - start_time) * 1000

                tool_invocations.append(
                    ToolInvocation(
                        tool_name=tool_name,
                        tool_input=tool_input,
                        tool_result=tool_result,
                        duration_ms=elapsed_ms,
                    )
                )

                import json

                tool_results_content.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": json.dumps(tool_result),
                    }
                )

            messages.append({"role": "user", "content": tool_results_content})

        # Exhausted max rounds — return what we have
        logger.warning("Tool use loop hit max rounds (%d)", max_tool_rounds)
        self._total_input_tokens += total_input
        self._total_output_tokens += total_output
        result = LLMResult(
            content="[Agent reached maximum tool invocation rounds]",
            stance=AgentStance.NEUTRAL,
            input_tokens=total_input,
            output_tokens=total_output,
            tool_invocations=tool_invocations,
        )
        return result

    async def generate_synthesis(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate a free-form synthesis response via Claude."""
        self._call_count += 1

        synthesis_tokens = max_tokens or (self.max_tokens * 2)
        message = await self.client.messages.create(
            model=self.model,
            max_tokens=synthesis_tokens,
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
