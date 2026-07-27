"""
Direct Neo4j driver client — replaces the neo4j-mcp-server subprocess.
Provides drop-in LangChain tools with the same invoke/ainvoke interface
so that graph nodes and routes need zero changes.

Lifecycle:
  - start() is called once at FastAPI startup (via lifespan)
  - stop() is called once at FastAPI shutdown
  - All nodes call get_tools() / find_tool() to execute Cypher via direct driver
"""
from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from neo4j import GraphDatabase, Driver
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class _CypherInput(BaseModel):
    query: str = Field(description="Cypher query string")
    params: dict[str, Any] = Field(default_factory=dict, description="Query parameters")


class _ReadCypherTool(BaseTool):
    name: str = "read_query"
    description: str = "Execute a read-only Cypher query against Neo4j"
    args_schema: type = _CypherInput
    _driver: Driver | None = None

    def _run(self, query: str, params: dict[str, Any] | None = None, **kwargs: Any) -> str:
        with self._driver.session() as session:
            result = session.run(query, **(params or {}))
            rows = [dict(r) for r in result]
            return json.dumps(rows, default=str)

    async def _arun(self, query: str, params: dict[str, Any] | None = None, **kwargs: Any) -> str:
        return self._run(query, params)


class _WriteCypherTool(BaseTool):
    name: str = "write_query"
    description: str = "Execute a write Cypher query against Neo4j"
    args_schema: type = _CypherInput
    _driver: Driver | None = None

    def _run(self, query: str, params: dict[str, Any] | None = None, **kwargs: Any) -> str:
        with self._driver.session() as session:
            result = session.run(query, **(params or {}))
            summary = result.consume()
            return json.dumps({"counters": summary.counters.__dict__ if hasattr(summary.counters, "__dict__") else str(summary.counters)}, default=str)

    async def _arun(self, query: str, params: dict[str, Any] | None = None, **kwargs: Any) -> str:
        return self._run(query, params)


class DirectClientManager:
    """
    Drop-in replacement for MCPClientManager.
    Exposes read_query / write_query LangChain tools backed by the Neo4j driver directly.
    """

    def __init__(self) -> None:
        self._driver: Driver | None = None
        self._tools: list[BaseTool] = []
        self._tool_map: dict[str, BaseTool] = {}

    async def start(self) -> None:
        settings = get_settings()
        logger.info("Connecting to Neo4j at %s as %s …", settings.neo4j_uri, settings.neo4j_username)
        self._driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_username, settings.neo4j_password),
        )
        self._driver.verify_connectivity()
        logger.info("Neo4j connection established.")

        read_tool = _ReadCypherTool()
        read_tool._driver = self._driver
        write_tool = _WriteCypherTool()
        write_tool._driver = self._driver

        self._tools = [read_tool, write_tool]
        self._tool_map = {t.name: t for t in self._tools}
        logger.info("Direct client ready — tools: %s", list(self._tool_map.keys()))

    async def stop(self) -> None:
        if self._driver:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed.")

    def get_tools(self) -> list[BaseTool]:
        return self._tools

    def find_tool(self, *name_fragments: str) -> BaseTool | None:
        fragments = [f.lower() for f in name_fragments]
        for name, tool in self._tool_map.items():
            if all(frag in name.lower() for frag in fragments):
                return tool
        return None

    def find_read_tool(self) -> BaseTool | None:
        return self._tool_map.get("read_query")

    def find_write_tool(self) -> BaseTool | None:
        return self._tool_map.get("write_query")


mcp_manager = DirectClientManager()
