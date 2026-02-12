"""Tool interface and result models for agent research tools."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
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
    source_id: str = ""          # PMID, internal record ID, etc.
    source_type: str = ""        # "pubmed", "internal", "web"
    relevance_score: float = 0.0
    snippet: str = ""


class ToolResult(BaseModel):
    """Structured result from a tool invocation."""
    source: str                  # "pubmed", "company_docs", "web"
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

    def _format_citation_ref(self, result: SearchResult) -> str:
        """Format a citation reference string for prompt injection."""
        if result.source_type == "pubmed" and result.source_id:
            return f"[PUBMED:{result.source_id}]"
        if result.source_type == "internal" and result.source_id:
            return f"[INTERNAL:{result.source_id}]"
        if result.url:
            return f"[WEB:{result.url}]"
        return f"[{result.source_type.upper()}:{result.title[:50]}]"


# Backward compatibility alias
AgentTool = BaseSearchTool
