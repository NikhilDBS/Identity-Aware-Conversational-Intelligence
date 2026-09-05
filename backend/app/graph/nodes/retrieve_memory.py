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


# Detect "fetch everything" intents regardless of phrasing
# ("Retrieve all available long-term memories..." vs "All stored information...").
# Rule: standalone word "all" + a scope word (memory/memories, information,
# stored, details, data, history), or an explicit everything/history phrase.
# Detected on the intent, not the keyword, because keyword extraction keeps
# leading verbs like "retrieve".
_BROAD_SCOPE_SUBSTRINGS = (
    "memor", "information", "stored", "detail", "data", "histor",
)
_BROAD_EXPLICIT_PHRASES = (
    "everything", "entire history", "full history",
)

_ALL_MEMORY_TYPES = ("identity", "episodic", "emotional")


def _is_broad_intent(intent: str) -> bool:
    text = intent.lower()
    if any(phrase in text for phrase in _BROAD_EXPLICIT_PHRASES):
        return True
    has_all = " all " in f" {text} "
    has_scope = any(scope in text for scope in _BROAD_SCOPE_SUBSTRINGS)
    return has_all and has_scope


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
    intents = state.get("retrieval_queries", [])

    all_results: list[dict[str, Any]] = []

    for entry in intents:
        # Accept both the structured {"description", "memory_types"} shape and
        # legacy plain-string intents.
        if isinstance(entry, dict):
            intent = entry.get("description", "")
            declared_types = [t for t in entry.get("memory_types", [])
                              if t in _ALL_MEMORY_TYPES]
        else:
            intent = entry
            declared_types = []

        keyword = _extract_keyword(intent)
        broad = _is_broad_intent(intent)
        # Broad "tell me everything" intents always fan out across all three
        # memory types; specific intents use the declared types (falling back
        # to a keyword guess for legacy string entries).
        memory_types = (list(_ALL_MEMORY_TYPES) if broad
                        else (declared_types or [_guess_memory_type(intent)]))

        for memory_type in memory_types:
            query, params = build_read_params(keyword, memory_type,
                                              force_all=broad)

            logger.info("retrieve_memory: intent=%r  type=%s  keyword=%r  broad=%s",
                        intent, memory_type, keyword, broad)
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
