"""Company/internal documentation search tool."""

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from colloquip.tools.interface import BaseSearchTool, SearchResult, ToolResult

logger = logging.getLogger(__name__)


class CompanyDocsTool(BaseSearchTool):
    """Search internal company literature and documentation.

    Searches a local directory of markdown/text files using keyword matching.
    Extensible — swap the search implementation for Elasticsearch, vector DB, etc.
    """

    _name = "company_docs"
    _description = (
        "Search the company's internal literature and documentation database. "
        "Returns relevant documents, reports, and internal data summaries."
    )

    def __init__(
        self,
        doc_path: Optional[str] = None,
        max_results: int = 5,
    ):
        self.doc_path = Path(doc_path) if doc_path else None
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
                            "Search query for internal documents. "
                            "Use specific terms like compound IDs, project names, "
                            "or assay types for best results."
                        ),
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results to return (1-10)",
                        "default": self.max_results,
                    },
                },
                "required": ["query"],
            },
        }

    async def execute(self, **kwargs) -> ToolResult:
        """Search internal documents by keyword matching."""
        query = kwargs.get("query", "")
        max_results = min(kwargs.get("max_results", self.max_results), 10)

        if not query:
            return ToolResult(source="company_docs", query=query, error="Empty query")

        if not self.doc_path or not self.doc_path.exists():
            return ToolResult(
                source="company_docs", query=query,
                error="Document path not configured or does not exist",
            )

        start_time = time.monotonic()
        try:
            results = self._search_files(query, max_results)
            return ToolResult(
                source="company_docs",
                query=query,
                results=results,
                execution_time_ms=(time.monotonic() - start_time) * 1000,
            )
        except Exception as e:
            logger.error("Company docs search failed: %s", e)
            return ToolResult(
                source="company_docs", query=query, error=str(e),
                execution_time_ms=(time.monotonic() - start_time) * 1000,
            )

    def _search_files(self, query: str, max_results: int) -> List[SearchResult]:
        """Simple keyword-based search across local documents."""
        query_tokens = set(query.lower().split())
        scored_results: List[tuple] = []

        extensions = {".md", ".txt", ".rst", ".csv"}
        for path in self.doc_path.rglob("*"):
            if path.suffix not in extensions or not path.is_file():
                continue

            try:
                full_content = path.read_text(errors="replace")
                content = full_content[:10000]
                if len(full_content) > 10000:
                    logger.debug("Truncated %s (%d chars) for search", path.name, len(full_content))
            except Exception:
                continue

            content_lower = content.lower()
            score = sum(1 for token in query_tokens if token in content_lower)
            if score > 0:
                scored_results.append((score, path, content))

        scored_results.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, path, content in scored_results[:max_results]:
            # Find the best snippet containing query terms
            snippet = self._extract_snippet(content, query_tokens)
            record_id = path.stem.replace(" ", "_")

            results.append(SearchResult(
                title=path.stem.replace("_", " ").replace("-", " ").title(),
                abstract=snippet,
                source_id=record_id,
                source_type="internal",
                relevance_score=min(score / len(query_tokens), 1.0) if query_tokens else 0.0,
                snippet=snippet[:300],
            ))

        return results

    def _extract_snippet(self, content: str, query_tokens: set, window: int = 200) -> str:
        """Extract the most relevant snippet from content around query terms."""
        content_lower = content.lower()
        best_pos = 0
        best_score = 0

        for token in query_tokens:
            pos = content_lower.find(token)
            if pos >= 0:
                # Count nearby tokens
                local = content_lower[max(0, pos - window):pos + window]
                local_score = sum(1 for t in query_tokens if t in local)
                if local_score > best_score:
                    best_score = local_score
                    best_pos = pos

        start = max(0, best_pos - window // 2)
        end = min(len(content), start + window)
        snippet = content[start:end].strip()

        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."

        return snippet


class MockCompanyDocsTool(BaseSearchTool):
    """Mock company docs tool for testing."""

    _name = "company_docs"
    _description = "Search internal documents (mock mode)"

    def __init__(self, max_results: int = 5):
        self.max_results = max_results

    @property
    def tool_schema(self) -> Dict[str, Any]:
        return {
            "name": self._name,
            "description": self._description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "default": self.max_results},
                },
                "required": ["query"],
            },
        }

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        max_results = kwargs.get("max_results", self.max_results)

        mock_results = [
            SearchResult(
                title=f"Internal Report: {query} Program Assessment",
                abstract=f"Internal analysis of {query} from the discovery team. "
                         f"Key findings include favorable selectivity profile and "
                         f"preliminary in vivo efficacy in disease-relevant models.",
                source_id="INT-2024-0142",
                source_type="internal",
                relevance_score=0.9,
                snippet=f"Favorable selectivity profile for {query}.",
            ),
            SearchResult(
                title=f"Assay Protocol: {query} Screening Campaign",
                abstract=f"Standardized protocol for high-throughput screening of "
                         f"{query}-related compounds. Includes IC50 determination "
                         f"and counter-screening methodology.",
                source_id="INT-2024-0089",
                source_type="internal",
                relevance_score=0.7,
                snippet=f"HTS protocol for {query} screening.",
            ),
        ]

        return ToolResult(
            source="company_docs",
            query=query,
            results=mock_results[:max_results],
            execution_time_ms=50.0,
        )
