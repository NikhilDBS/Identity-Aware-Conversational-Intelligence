"""
FastAPI routes — the primary API surface.

Endpoints:
  POST /chat              — run the full LangGraph pipeline, return response + trace
  GET  /memory/{user_id}  — debug dump of all memories for a user
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException

from app.graph.graph_builder import compiled_graph
from app.graph.state import PipelineState
from app.mcp.client import mcp_manager
from app.mcp.cypher_templates import READ_ALL_USER_MEMORIES
from app.models.schemas import ChatRequest, ChatResponse, TraceEntry

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Run the identity-aware conversational pipeline for one user turn.

    Returns the assistant's response and a full debug trace of every
    pipeline decision (retrieval, extraction, writes).
    """
    message_id = str(uuid.uuid4())

    initial_state: PipelineState = {
        "user_id":           request.user_id,
        "conversation_id":   request.conversation_id,
        "user_message":      request.message,
        "message_id":        message_id,
        "needs_retrieval":   False,
        "retrieval_queries": [],
        "retrieved_context": [],
        "extracted_memories": [],
        "final_response":    "",
        "trace":             [],
    }

    try:
        final_state = await compiled_graph.ainvoke(initial_state)
    except Exception as exc:
        logger.exception("Pipeline failed for user %s: %s", request.user_id, exc)
        raise HTTPException(status_code=500, detail=f"Pipeline error: {exc}")

    trace_entries = [
        TraceEntry(
            node=t.get("node", "unknown"),
            timestamp=t.get("timestamp", datetime.utcnow().isoformat()),
            data={k: v for k, v in t.items() if k not in ("node", "timestamp")},
        )
        for t in final_state.get("trace", [])
    ]

    return ChatResponse(
        response=final_state.get("final_response", ""),
        conversation_id=request.conversation_id,
        trace=trace_entries,
    )


@router.get("/memory/{user_id}")
async def get_user_memory(user_id: str) -> dict[str, Any]:
    """
    Debug endpoint: dump all memories stored for a user.
    Useful for inspecting the graph state during research/development.
    """
    import json

    tool = mcp_manager.find_read_tool()
    if tool is None:
        raise HTTPException(status_code=503, detail="MCP read tool not available")

    try:
        result = await tool.ainvoke({
            "query":  READ_ALL_USER_MEMORIES,
            "params": {"user_id": user_id},
        })
        if isinstance(result, str):
            data = json.loads(result) if result.strip().startswith(("{", "[")) else {"raw": result}
        elif isinstance(result, (dict, list)):
            data = result
        else:
            data = {"raw": str(result)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {"user_id": user_id, "memories": data}
