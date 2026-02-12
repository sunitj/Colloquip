"""Tool registry: maps tool names to implementations, configures per subreddit."""

import logging
from typing import Any, Dict, List, Optional, Type

from colloquip.tools.interface import AgentTool, BaseSearchTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Maps tool IDs to implementations and configures them per subreddit.

    Maintains both real and mock implementations. In mock mode, returns
    mock tools that don't make network calls.
    """

    def __init__(self, mock_mode: bool = False):
        self.mock_mode = mock_mode
        self._tool_factories: Dict[str, Dict[str, Any]] = {}
        self._register_defaults()

    def _register_defaults(self):
        """Register the built-in tool types."""
        from colloquip.tools.pubmed import MockPubMedTool, PubMedTool
        from colloquip.tools.company_docs import CompanyDocsTool, MockCompanyDocsTool
        from colloquip.tools.web_search import MockWebSearchTool, WebSearchTool

        self._tool_factories["pubmed_search"] = {
            "real": PubMedTool,
            "mock": MockPubMedTool,
        }
        self._tool_factories["company_docs"] = {
            "real": CompanyDocsTool,
            "mock": MockCompanyDocsTool,
        }
        self._tool_factories["web_search"] = {
            "real": WebSearchTool,
            "mock": MockWebSearchTool,
        }

    def register_tool(
        self,
        tool_id: str,
        real_class: Type,
        mock_class: Type,
    ):
        """Register a custom tool type."""
        self._tool_factories[tool_id] = {
            "real": real_class,
            "mock": mock_class,
        }

    def create_tool(
        self,
        tool_id: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> BaseSearchTool:
        """Create a tool instance by ID with optional configuration."""
        if tool_id not in self._tool_factories:
            raise ValueError(
                f"Unknown tool '{tool_id}'. "
                f"Available: {list(self._tool_factories.keys())}"
            )

        factory = self._tool_factories[tool_id]
        cls = factory["mock"] if self.mock_mode else factory["real"]
        kwargs = config or {}
        return cls(**kwargs)

    def get_tools_for_subreddit(
        self,
        tool_configs: Optional[List[Dict[str, Any]]] = None,
    ) -> List[BaseSearchTool]:
        """Create tool instances based on a subreddit's tool configuration.

        Args:
            tool_configs: List of dicts with 'tool_id' and optional 'connection_config'.
                          Matches the ToolConfig model from models.py.
        """
        if not tool_configs:
            return []
        tools = []
        for tc in tool_configs:
            tool_id = tc.get("tool_id", "")
            config = tc.get("connection_config", {})
            enabled = tc.get("enabled", True)

            if not enabled:
                continue

            try:
                tool = self.create_tool(tool_id, config)
                tools.append(tool)
            except ValueError as e:
                logger.warning("Skipping tool: %s", e)

        return tools

    def get_claude_tool_schemas(
        self,
        tools: List[BaseSearchTool],
    ) -> List[Dict[str, Any]]:
        """Convert tool instances to Claude API tool-use format."""
        return [tool.tool_schema for tool in tools]

    def available_tools(self) -> List[str]:
        """List registered tool IDs."""
        return list(self._tool_factories.keys())

    async def execute_tool_call(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tools: List[BaseSearchTool],
    ) -> Dict[str, Any]:
        """Execute a tool call by name from a list of available tools.

        Used by the LLM integration layer to dispatch tool calls
        from Claude's tool_use response blocks.
        """
        for tool in tools:
            if tool.name == tool_name:
                result = await tool.execute(**tool_input)
                return result.model_dump()

        return {"error": f"Tool '{tool_name}' not found in available tools"}
