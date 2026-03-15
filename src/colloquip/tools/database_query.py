"""Database query tool for agent-driven data exploration.

Allows agents to execute read-only SQL queries against user-configured
database connections. Queries are validated to be SELECT-only.
"""

import logging
import re
from typing import Any, Dict

from colloquip.tools.interface import BaseSearchTool, SearchResult, ToolResult

logger = logging.getLogger(__name__)

# Pattern to detect non-SELECT statements
_WRITE_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|REPLACE|MERGE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)


def validate_read_only(sql: str) -> bool:
    """Validate that a SQL query is read-only (SELECT statements only).

    Returns True if the query appears safe (SELECT-only), False otherwise.
    """
    # Strip comments
    cleaned = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)
    cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)
    cleaned = cleaned.strip().rstrip(";").strip()

    if not cleaned:
        return False

    # Must start with SELECT or WITH (for CTEs)
    if not re.match(r"^\s*(SELECT|WITH)\b", cleaned, re.IGNORECASE):
        return False

    # Must not contain write operations
    if _WRITE_PATTERN.search(cleaned):
        return False

    return True


class DatabaseQueryTool(BaseSearchTool):
    """Tool for querying user-configured databases.

    Executes read-only SQL queries and returns results as structured data.
    Requires an async database engine to be provided.
    """

    _name = "database_query"
    _description = (
        "Execute a read-only SQL query against a configured database. "
        "Use this to explore experimental data, compound libraries, "
        "assay results, or other internal data sources."
    )

    def __init__(self, connection_name: str = "", **kwargs):
        self.connection_name = connection_name
        self._engine = None

    def set_engine(self, engine):
        """Set the async SQLAlchemy engine for query execution."""
        self._engine = engine

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
                            "SQL SELECT query to execute. Only read-only queries are allowed."
                        ),
                    },
                    "max_rows": {
                        "type": "integer",
                        "description": "Maximum number of rows to return (default 50, max 200).",
                        "default": 50,
                    },
                },
                "required": ["query"],
            },
        }

    async def execute(self, **kwargs) -> ToolResult:
        import time

        start = time.monotonic()
        query = kwargs.get("query", "")
        max_rows = min(kwargs.get("max_rows", 50), 200)

        if not validate_read_only(query):
            return ToolResult(
                source="database",
                query=query,
                error="Query rejected: only SELECT statements are allowed.",
            )

        if not self._engine:
            return ToolResult(
                source="database",
                query=query,
                error="No database engine configured.",
            )

        try:
            from sqlalchemy import text
            from sqlalchemy.ext.asyncio import AsyncSession

            async with AsyncSession(self._engine) as session:
                result = await session.execute(text(query))
                columns = list(result.keys()) if result.returns_rows else []
                rows = result.fetchmany(max_rows) if result.returns_rows else []

                search_results = []
                for row in rows:
                    row_dict = dict(zip(columns, row))
                    search_results.append(
                        SearchResult(
                            title=str(row_dict.get(columns[0], "")) if columns else "row",
                            abstract=str(row_dict),
                            source_type="database",
                            source_id=self.connection_name,
                        )
                    )

                elapsed = (time.monotonic() - start) * 1000
                return ToolResult(
                    source="database",
                    query=query,
                    results=search_results,
                    truncated=len(rows) >= max_rows,
                    execution_time_ms=elapsed,
                )

        except Exception as e:
            logger.error("Database query failed: %s", e)
            elapsed = (time.monotonic() - start) * 1000
            return ToolResult(
                source="database",
                query=query,
                error=f"Query execution failed: {e}",
                execution_time_ms=elapsed,
            )


class MockDatabaseQueryTool(BaseSearchTool):
    """Mock database query tool for testing."""

    _name = "database_query"
    _description = "Execute a read-only SQL query against a configured database."

    @property
    def tool_schema(self) -> Dict[str, Any]:
        return {
            "name": self._name,
            "description": self._description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "SQL SELECT query."},
                    "max_rows": {"type": "integer", "default": 50},
                },
                "required": ["query"],
            },
        }

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")

        if not validate_read_only(query):
            return ToolResult(
                source="database",
                query=query,
                error="Query rejected: only SELECT statements are allowed.",
            )

        return ToolResult(
            source="database",
            query=query,
            results=[
                SearchResult(
                    title="compound_A",
                    abstract=(
                        "{'id': 1, 'name': 'compound_A', 'ic50_nm': 12.5, "
                        "'selectivity': 0.95, 'target': 'EGFR'}"
                    ),
                    source_type="database",
                    source_id="mock_db",
                ),
                SearchResult(
                    title="compound_B",
                    abstract=(
                        "{'id': 2, 'name': 'compound_B', 'ic50_nm': 8.3, "
                        "'selectivity': 0.87, 'target': 'EGFR'}"
                    ),
                    source_type="database",
                    source_id="mock_db",
                ),
            ],
            execution_time_ms=1.0,
        )
