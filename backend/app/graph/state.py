"""
LangGraph pipeline state — the single TypedDict shared across all nodes.
Every node receives this state and returns a partial update dict.
"""
from __future__ import annotations
from typing import TypedDict, Any


class PipelineState(TypedDict):
    # ── Input ────────────────────────────────────────────────────────────────
    # Single-user system: no user_id — memories are global nodes.
    conversation_id: str
    user_message:    str
    message_id:      str          # UUID for the Message node being processed

    # ── assess_context output ─────────────────────────────────────────────────
    needs_retrieval:    bool
    # Each entry: {"description": <natural-language intent>,
    #              "memory_types": ["identity"|"episodic"|"emotional", ...]}
    # (legacy plain-string entries are still accepted and type-guessed)
    retrieval_queries:  list[dict[str, Any]]

    # ── retrieve_memory output ────────────────────────────────────────────────
    retrieved_context:  list[dict[str, Any]]

    # ── extract_and_classify output ───────────────────────────────────────────
    extracted_memories: list[dict[str, Any]]  # typed, classified memory payloads

    # ── generate_response output ──────────────────────────────────────────────
    final_response: str

    # ── Research/debug trace (every node appends here) ────────────────────────
    trace: list[dict[str, Any]]
