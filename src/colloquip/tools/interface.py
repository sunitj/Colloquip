"""Tool interface and result models for agent research tools."""

import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """A single search result from a literature or data source."""

    title: str
    authors: List[str] = Field(default_factory=list)
    abstract: str = ""
    url: str = ""
    doi: str = ""
    year: Optional[int] = None
    source_id: str = ""  # PMID, internal record ID, etc.
    source_type: str = ""  # "pubmed", "internal", "web"
    relevance_score: float = 0.0
    snippet: str = ""


class ToolResult(BaseModel):
    """Structured result from a tool invocation."""

    source: str  # "pubmed", "company_docs", "web"
    query: str
    results: List[SearchResult] = Field(default_factory=list)
    truncated: bool = False
    error: Optional[str] = None
    execution_time_ms: float = 0.0


class BaseSearchTool(ABC):
    """Abstract base class for search tools.

    All tool implementations must inherit from this and implement
    tool_schema and execute(). Shared functionality (citation formatting)
    lives here.
    """

    _name: str = ""
    _description: str = ""

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    @abstractmethod
    def tool_schema(self) -> Dict[str, Any]:
        """Claude API tool-use schema for this tool."""
        ...

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters and return results."""
        ...

    @staticmethod
    def _sanitize_citation_field(value: str, max_len: int = 100) -> str:
        """Strip control characters and prompt-injection markers from a citation field."""
        # Remove common prompt injection markers and control chars
        sanitized = re.sub(r"[\x00-\x1f\x7f]", "", value)
        # Strip markdown/instruction-like patterns that could manipulate agent behavior
        sanitized = re.sub(r"<\|.*?\|>", "", sanitized)
        sanitized = re.sub(r"\[INST\].*?\[/INST\]", "", sanitized, flags=re.DOTALL)
        return sanitized[:max_len].strip()

    def _format_citation_ref(self, result: SearchResult) -> str:
        """Format a sanitized citation reference string."""
        if result.source_type == "pubmed" and result.source_id:
            sid = self._sanitize_citation_field(result.source_id, max_len=20)
            return f"[PUBMED:{sid}]"
        if result.source_type == "internal" and result.source_id:
            sid = self._sanitize_citation_field(result.source_id, max_len=50)
            return f"[INTERNAL:{sid}]"
        if result.url:
            url = self._sanitize_citation_field(result.url, max_len=200)
            return f"[WEB:{url}]"
        title = self._sanitize_citation_field(result.title, max_len=50)
        stype = self._sanitize_citation_field(result.source_type, max_len=20).upper()
        return f"[{stype}:{title}]"


# Backward compatibility alias
AgentTool = BaseSearchTool
