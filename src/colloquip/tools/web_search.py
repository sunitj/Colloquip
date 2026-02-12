"""Web/academic search tool using Semantic Scholar API."""

import logging
import time
from typing import Any, Dict, List, Optional

from colloquip.tools.interface import BaseSearchTool, SearchResult, ToolResult

logger = logging.getLogger(__name__)

_SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1"


class WebSearchTool(BaseSearchTool):
    """Search academic literature via Semantic Scholar API.

    Semantic Scholar is free and provides structured academic results
    including citations, abstracts, and paper metadata.
    """

    _name = "web_search"
    _description = (
        "Search academic literature and web sources for relevant research. "
        "Returns papers with titles, abstracts, authors, and citation counts."
    )

    def __init__(
        self,
        api_key: Optional[str] = None,
        max_results: int = 5,
    ):
        self.api_key = api_key
        self.max_results = max_results

    @property
    def tool_schema(self) -> Dict[str, Any]:
        return {
            "name": self._name,
            "description": self._description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Search query for academic papers. "
                            "Use specific scientific terms for best results."
                        ),
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results (1-10)",
                        "default": self.max_results,
                    },
                },
                "required": ["query"],
            },
        }

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        max_results = min(kwargs.get("max_results", self.max_results), 10)

        if not query:
            return ToolResult(source="web", query=query, error="Empty query")

        start_time = time.monotonic()
        try:
            results = await self._search(query, max_results)
            return ToolResult(
                source="web",
                query=query,
                results=results,
                truncated=len(results) >= max_results,
                execution_time_ms=(time.monotonic() - start_time) * 1000,
            )
        except Exception as e:
            logger.error("Web search failed: %s", e)
            return ToolResult(
                source="web", query=query, error=str(e),
                execution_time_ms=(time.monotonic() - start_time) * 1000,
            )

    async def _search(self, query: str, max_results: int) -> List[SearchResult]:
        try:
            import httpx
        except ImportError:
            raise ImportError("httpx required for web search: pip install httpx")

        headers = {}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        params = {
            "query": query,
            "limit": max_results,
            "fields": "title,abstract,authors,year,externalIds,url,citationCount",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{_SEMANTIC_SCHOLAR_BASE}/paper/search",
                params=params,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for paper in data.get("data", []):
            authors = [
                a.get("name", "") for a in paper.get("authors", [])
            ][:5]

            doi = ""
            external_ids = paper.get("externalIds") or {}
            if external_ids.get("DOI"):
                doi = external_ids["DOI"]

            pmid = external_ids.get("PubMed", "")

            abstract = paper.get("abstract") or ""

            results.append(SearchResult(
                title=paper.get("title", ""),
                authors=authors,
                abstract=abstract[:1000],
                url=paper.get("url", ""),
                doi=doi,
                year=paper.get("year"),
                source_id=pmid or doi or paper.get("paperId", ""),
                source_type="web",
                snippet=abstract[:300] if abstract else paper.get("title", ""),
            ))

        return results


class MockWebSearchTool(WebSearchTool):
    """Mock web search tool for testing.

    Inherits schema from WebSearchTool; overrides execute() with canned data.
    """

    _description = "Search academic literature (mock mode)"

    def __init__(self, max_results: int = 5):
        super().__init__(max_results=max_results)

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        max_results = kwargs.get("max_results", self.max_results)

        mock_results = [
            SearchResult(
                title=f"Recent advances in {query}: a comprehensive review",
                authors=["Garcia R", "Kumar S", "Thompson L"],
                abstract=f"This review covers recent advances in {query}, "
                         f"highlighting key developments in the field and "
                         f"identifying emerging research directions.",
                url="https://www.semanticscholar.org/paper/mock-001",
                doi="10.5555/mock.2024.001",
                year=2024,
                source_id="mock-ss-001",
                source_type="web",
                snippet=f"Review of recent advances in {query}.",
            ),
        ]

        return ToolResult(
            source="web",
            query=query,
            results=mock_results[:max_results],
            execution_time_ms=100.0,
        )
