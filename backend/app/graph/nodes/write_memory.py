"""
Node 4: write_memory  (conditional — only runs if extracted_memories is non-empty)
───────────────────────────────────────────────────────────────────────────────────
For each extracted memory:
  1. Select the appropriate Cypher write template
  2. Execute via the MCP write tool
  3. The template automatically links the new node back to the Message via PRODUCED

Also writes the Conversation and Message nodes if they don't yet exist
(idempotent MERGE operations).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from app.graph.state import PipelineState
from app.mcp.client import mcp_manager
from app.mcp.cypher_templates import (
    WRITE_CONVERSATION,
    WRITE_MESSAGE,
    build_write_params,
)

logger = logging.getLogger(__name__)


async def _run_cypher_write(query: str, params: dict[str, Any]) -> dict[str, Any]:
    """Execute a write Cypher query via the MCP tool."""
    tool = mcp_manager.find_write_tool()
    if tool is None:
        logger.error("No write tool found in MCP server. Available: %s",
                     [t.name for t in mcp_manager.get_tools()])
        return {"error": "no write tool"}

    try:
        result = await tool.ainvoke({"query": query, "params": params})
        if isinstance(result, str):
            return json.loads(result) if result.strip().startswith("{") else {"raw": result}
        return result if isinstance(result, dict) else {"raw": str(result)}
    except Exception as exc:
        logger.warning("MCP write failed: %s", exc)
        return {"error": str(exc)}


async def write_memory(state: PipelineState) -> dict[str, Any]:
    ts = datetime.utcnow().isoformat()
    conversation_id = state["conversation_id"]
    message_id      = state["message_id"]
    memories        = state.get("extracted_memories", [])

    # ── 1. Ensure Conversation node exists ────────────────────────────────────
    await _run_cypher_write(WRITE_CONVERSATION, {
        "conversation_id": conversation_id,
        "now":             ts,
    })

    # ── 2. Ensure Message node exists and is linked to Conversation ───────────
    await _run_cypher_write(WRITE_MESSAGE, {
        "message_id":      message_id,
        "conversation_id": conversation_id,
        "role":            "user",
        "content":         state["user_message"],
        "timestamp":       ts,
    })

    # ── 3. Write each extracted memory ────────────────────────────────────────
    write_results: list[dict[str, Any]] = []
    episodic_ids:  list[str] = []
    emotional_ids: list[str] = []

    for mem in memories:
        memory_type = mem.get("memory_type")
        try:
            query, params = build_write_params(message_id, memory_type, mem)
            result = await _run_cypher_write(query, params)

            memory_id = params["memory_id"]
            write_results.append({
                "memory_type": memory_type,
                "memory_id":   memory_id,
                "content":     mem.get("content", ""),
                "result":      result,
            })

            if memory_type == "episodic":
                episodic_ids.append(memory_id)
            elif memory_type == "emotional":
                emotional_ids.append(memory_id)

            logger.info("Wrote %s memory: %s", memory_type, mem.get("content", "")[:60])
        except Exception as exc:
            logger.error("Failed to write %s memory: %s", memory_type, exc)
            write_results.append({"memory_type": memory_type, "error": str(exc)})

    # ── 4. Link episodic → emotional (EVOKED) when co-present in same turn ────
    if episodic_ids and emotional_ids:
        from app.mcp.cypher_templates import LINK_EPISODIC_TO_EMOTIONAL
        for ep_id in episodic_ids:
            for emo_id in emotional_ids:
                await _run_cypher_write(LINK_EPISODIC_TO_EMOTIONAL, {
                    "episodic_id":  ep_id,
                    "emotional_id": emo_id,
                })
                logger.info("Linked episodic %s → emotional %s (EVOKED)", ep_id, emo_id)

    trace_entry = {
        "node":          "write_memory",
        "timestamp":     ts,
        "writes":        len(write_results),
        "write_results": write_results,
    }

    return {
        "trace": state.get("trace", []) + [trace_entry],
    }
