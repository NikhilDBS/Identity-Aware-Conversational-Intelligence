"""
LangGraph pipeline state — the single TypedDict shared across all nodes.
Every node receives this state and returns a partial update dict.
"""
from __future__ import annotations
from typing import TypedDict, Any


class PipelineState(TypedDict):
    # ── Input ────────────────────────────────────────────────────────────────
    user_id:         str
    conversation_id: str
    user_message:    str
    message_id:      str          # UUID for the Message node being processed

    # ── assess_context output ─────────────────────────────────────────────────
    needs_retrieval:    bool
    retrieval_queries:  list[str]  # natural-language intents for retrieval

    # ── retrieve_memory output ────────────────────────────────────────────────
    retrieved_context:  list[dict[str, Any]]

    # ── extract_and_classify output ───────────────────────────────────────────
    extracted_memories: list[dict[str, Any]]  # typed, classified memory payloads

    # ── generate_response output ──────────────────────────────────────────────
    final_response: str

    # ── Research/debug trace (every node appends here) ────────────────────────
    trace: list[dict[str, Any]]
