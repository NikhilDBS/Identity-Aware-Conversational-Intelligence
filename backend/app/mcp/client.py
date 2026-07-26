"""
MCP client manager — launches the neo4j-mcp-server as a stdio subprocess
via langchain-mcp-adapters and exposes its tools as native LangChain tools.

Lifecycle:
  - start() is called once at FastAPI startup (via lifespan)
  - stop() is called once at FastAPI shutdown
  - All nodes call get_tools() / find_tool() to execute Cypher via MCP
"""
from __future__ import annotations

import logging
import os
from typing import Any

from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)


class MCPClientManager:
    """
    Wraps the langchain-mcp-adapters MultiServerMCPClient.
    Manages the lifecycle of the neo4j-mcp-server subprocess.
    """

    def __init__(self) -> None:
        self._client: Any = None
        self._tools: list[BaseTool] = []
        self._tool_map: dict[str, BaseTool] = {}

    async def start(self) -> None:
        """Start the MCP server subprocess and load its tools."""
        from langchain_mcp_adapters.client import MultiServerMCPClient
        from app.core.config import get_settings
        from neo4j_mcp_server import get_binary_path

        settings = get_settings()
        binary_path = get_binary_path()
        logger.info("Neo4j MCP server binary: %s", binary_path)

        mcp_env = {
            "NEO4J_URI":      settings.neo4j_uri,
            "NEO4J_USERNAME": settings.neo4j_username,
            "NEO4J_PASSWORD": settings.neo4j_password,
            "NEO4J_DATABASE": settings.neo4j_database,
            "NEO4J_READ_ONLY": "false",
            # Inherit PATH so the binary can find any needed libs
            **{k: v for k, v in os.environ.items() if k in ("PATH", "PYTHONPATH", "USERPROFILE", "HOME")},
        }

        server_config = {
            "neo4j": {
                "command": binary_path,
                "args": [],
                "env": mcp_env,
                "transport": "stdio",
            }
        }

        logger.info("Starting Neo4j MCP server subprocess …")
        self._client = MultiServerMCPClient(server_config)
        await self._client.__aenter__()

        self._tools = self._client.get_tools()
        self._tool_map = {t.name: t for t in self._tools}

        logger.info("MCP tools available: %s", list(self._tool_map.keys()))

    async def stop(self) -> None:
        """Shut down the MCP server subprocess cleanly."""
        if self._client is not None:
            try:
                await self._client.__aexit__(None, None, None)
                logger.info("MCP server subprocess stopped.")
            except Exception as exc:
                logger.warning("Error stopping MCP client: %s", exc)

    def get_tools(self) -> list[BaseTool]:
        return self._tools

    def find_tool(self, *name_fragments: str) -> BaseTool | None:
        """
        Find a tool whose name contains ALL of the given fragments (case-insensitive).
        Useful because the exact tool name depends on the MCP server version.
        Example: find_tool("read") → first tool whose name contains "read"
        """
        fragments = [f.lower() for f in name_fragments]
        for name, tool in self._tool_map.items():
            if all(frag in name.lower() for frag in fragments):
                return tool
        return None

    def find_read_tool(self) -> BaseTool | None:
        """Return the MCP read-query tool."""
        # Try common names used by neo4j-mcp-server
        for candidate in ("read_query", "read-query", "read_cypher", "execute_read"):
            if candidate in self._tool_map:
                return self._tool_map[candidate]
        return self.find_tool("read")

    def find_write_tool(self) -> BaseTool | None:
        """Return the MCP write-query tool."""
        for candidate in ("write_query", "write-query", "write_cypher", "execute_write"):
            if candidate in self._tool_map:
                return self._tool_map[candidate]
        return self.find_tool("write")


# Module-level singleton — imported by nodes and FastAPI lifespan
mcp_manager = MCPClientManager()
