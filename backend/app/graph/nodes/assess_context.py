"""
Node 1: assess_context
─────────────────────
Chain-of-thought LLM call that decides:
  - needs_retrieval: should past memory be fetched to understand this message?
  - retrieval_intents: what to look for (natural language), if retrieval is needed

Uses LiteLLM's acompletion with response_format for structured JSON output.
Never parsed free-text.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import litellm

from app.core.config import get_settings
from app.graph.state import PipelineState
from app.models.schemas import ContextAssessment

logger = logging.getLogger(__name__)

# Silence verbose litellm logs
litellm.suppress_debug_info = True


SYSTEM_PROMPT = """You are the context-assessment module for a conversational AI with persistent memory.

Your ONLY job is to decide:
1. Does answering this user message (or giving a truly personalized response) require looking up 
   past memories about the user? 
2. If yes — what specific information should be retrieved?

Think step by step before deciding. Consider:
- Is this a follow-up to something the user likely told us before?
- Does a genuinely helpful response depend on knowing the user's identity, past events, or emotional state?
- Would a reasonable response be the same regardless of who the user is? (→ no retrieval needed)

Return ONLY valid JSON matching this exact schema:
{
  "needs_retrieval": <bool>,
  "retrieval_intents": [
    {
      "description": "<what to look for>",
      "memory_types": ["identity" | "episodic" | "emotional"]
    }
  ],
  "reasoning": "<brief chain-of-thought>"
}
If needs_retrieval is false, retrieval_intents should be an empty array [].
"""


def make_user_prompt(message: str, recent_turns: list[dict]) -> str:
    history_text = ""
    if recent_turns:
        lines = [f"[{t.get('role', '?')}]: {t.get('content', '')}" for t in recent_turns[-6:]]
        history_text = "\n".join(lines)
    else:
        history_text = "(no prior conversation history)"

    return f"""Recent conversation:
{history_text}

New user message:
\"{message}\"

Assess whether past memory retrieval is needed and output the JSON."""


async def assess_context(state: PipelineState) -> dict[str, Any]:
    settings = get_settings()
    ts = datetime.utcnow().isoformat()

    recent_turns = state.get("retrieved_context", [])  # may be empty on first call
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": make_user_prompt(state["user_message"], recent_turns)},
    ]

    try:
        response = await litellm.acompletion(
            model=settings.litellm_model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        raw_json = response.choices[0].message.content
        data = json.loads(raw_json)
        assessment = ContextAssessment.model_validate(data)
        logger.info("assess_context: needs_retrieval=%s", assessment.needs_retrieval)
    except Exception as exc:
        logger.error("assess_context failed: %s", exc)
        # Safe fallback: skip retrieval, continue pipeline
        assessment = ContextAssessment(
            needs_retrieval=False,
            retrieval_intents=[],
            reasoning=f"Assessment failed ({exc}); defaulting to no retrieval.",
        )

    intents_text = [ri.description for ri in assessment.retrieval_intents]

    trace_entry = {
        "node":            "assess_context",
        "timestamp":       ts,
        "needs_retrieval": assessment.needs_retrieval,
        "intents":         intents_text,
        "reasoning":       assessment.reasoning,
    }

    return {
        "needs_retrieval":   assessment.needs_retrieval,
        "retrieval_queries": intents_text,
        "trace":             state.get("trace", []) + [trace_entry],
    }
