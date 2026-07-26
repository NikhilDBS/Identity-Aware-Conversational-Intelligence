"""
Node 2: retrieve_memory  (conditional — only runs if needs_retrieval is True)
──────────────────────────────────────────────────────────────────────────────
Translates each retrieval intent into Cypher using the template library,
calls the MCP read tool, and accumulates results in retrieved_context.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from app.graph.state import PipelineState
from app.mcp.client import mcp_manager
from app.mcp.cypher_templates import build_read_params
from app.models.schemas import MemoryType

logger = logging.getLogger(__name__)

# Map rough keywords in retrieval intents to memory types
_MEMORY_TYPE_KEYWORDS = {
    "identity":   ["identity", "trait", "preference", "value", "role", "relationship", "goal", "who"],
    "episodic":   ["episodic", "event", "experience", "happened", "did", "went", "interview", "travel", "history"],
    "emotional":  ["emotion", "emotional", "feel", "feeling", "mood", "anxious", "happy", "sad", "scared"],
}


def _guess_memory_type(intent: str) -> str:
    intent_lower = intent.lower()
    for mtype, keywords in _MEMORY_TYPE_KEYWORDS.items():
        if any(kw in intent_lower for kw in keywords):
            return mtype
    return "episodic"  # sensible default


def _extract_keyword(intent: str) -> str:
    """Extract a short keyword from a natural-language intent for template matching."""
    stop_words = {"check", "if", "user", "has", "mentioned", "before", "the", "a", "an",
                  "about", "related", "to", "any", "information", "on", "their", "find"}
    words = [w.strip(".,?") for w in intent.lower().split() if w not in stop_words]
    return " ".join(words[:3]) if words else intent[:30]


async def _run_cypher_read(query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    """Execute a read Cypher query via the MCP tool and return parsed results."""
    tool = mcp_manager.find_read_tool()
    if tool is None:
        logger.error("No read tool found in MCP server. Available: %s",
                     [t.name for t in mcp_manager.get_tools()])
        return []

    try:
        result = await tool.ainvoke({"query": query, "params": params})
        # MCP tool may return a string (JSON) or already-parsed data
        if isinstance(result, str):
            parsed = json.loads(result)
        elif isinstance(result, list):
            parsed = result
        elif isinstance(result, dict):
            parsed = result.get("results", result.get("data", [result]))
        else:
            parsed = []
        return parsed if isinstance(parsed, list) else [parsed]
    except Exception as exc:
        logger.warning("MCP read failed: %s", exc)
        return []


async def retrieve_memory(state: PipelineState) -> dict[str, Any]:
    ts = datetime.utcnow().isoformat()
    user_id = state["user_id"]
    intents = state.get("retrieval_queries", [])

    all_results: list[dict[str, Any]] = []

    for intent in intents:
        memory_type = _guess_memory_type(intent)
        keyword = _extract_keyword(intent)
        query, params = build_read_params(user_id, keyword, memory_type)

        logger.info("retrieve_memory: intent=%r  type=%s  keyword=%r", intent, memory_type, keyword)
        rows = await _run_cypher_read(query, params)

        all_results.append({
            "intent":      intent,
            "memory_type": memory_type,
            "keyword":     keyword,
            "results":     rows,
        })

    trace_entry = {
        "node":            "retrieve_memory",
        "timestamp":       ts,
        "intents_count":   len(intents),
        "results_summary": [
            {"intent": r["intent"], "rows_found": len(r["results"])}
            for r in all_results
        ],
    }

    return {
        "retrieved_context": all_results,
        "trace": state.get("trace", []) + [trace_entry],
    }
