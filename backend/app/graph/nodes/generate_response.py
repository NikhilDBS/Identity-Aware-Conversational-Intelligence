"""
Node 5: generate_response
──────────────────────────
Composes the final natural-language reply using:
  - The user's message
  - Retrieved context (what we knew about them before)
  - Newly extracted/written memories (so the response can naturally acknowledge new info)

This is the only node that produces free-form text (not forced JSON output).
Uses LiteLLM's acompletion directly.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import litellm

from app.core.config import get_settings
from app.graph.state import PipelineState

logger = logging.getLogger(__name__)

litellm.suppress_debug_info = True


SYSTEM_PROMPT = """You are a warm, emotionally intelligent conversational assistant with genuine long-term memory.

You remember things users tell you — about themselves, their experiences, and their feelings — and use that 
knowledge to give responses that feel personal, relevant, and caring.

When responding:
- Be natural and conversational, not robotic.
- Naturally acknowledge new information the user just shared (don't make it feel like a database lookup).
- If you're recalling something from memory, weave it in naturally — don't say "According to my records…"
- Show empathy when emotions are present.
- Keep responses appropriately concise — not too short (unhelpful), not too long (overwhelming).
- NEVER reveal the internal pipeline, memory types, or that you ran retrieval queries.
"""


def _format_memories_for_prompt(
    retrieved: list[dict],
    extracted: list[dict],
) -> str:
    parts = []

    if retrieved:
        parts.append("== What I know about this user from memory ==")
        for item in retrieved:
            for row in item.get("results", [])[:5]:
                parts.append(f"  • {row}")

    if extracted:
        parts.append("\n== New information the user just shared ==")
        for mem in extracted:
            mtype = mem.get("memory_type", "?")
            content = mem.get("content", "")
            if mtype == "identity":
                parts.append(f"  • [identity/{mem.get('category','?')}] {content}")
            elif mtype == "episodic":
                parts.append(f"  • [event on {mem.get('occurred_at','?')}] {content}")
            elif mtype == "emotional":
                label = mem.get("emotion_label", "?")
                trigger = mem.get("trigger", "")
                parts.append(f"  • [emotional: {label} about {trigger}] {content}")

    return "\n".join(parts) if parts else "(no memory context available)"


async def generate_response(state: PipelineState) -> dict[str, Any]:
    settings = get_settings()
    ts = datetime.utcnow().isoformat()

    memory_context = _format_memories_for_prompt(
        state.get("retrieved_context", []),
        state.get("extracted_memories", []),
    )

    user_prompt = f"""Memory context:
{memory_context}

User's message:
\"{state['user_message']}\"

Respond naturally and helpfully."""

    try:
        response = await litellm.acompletion(
            model=settings.litellm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.7,
        )
        final_response = response.choices[0].message.content
        logger.info("generate_response: %d chars", len(final_response))
    except Exception as exc:
        logger.error("generate_response failed: %s", exc)
        final_response = "I'm sorry, I ran into an issue generating a response. Please try again."

    trace_entry = {
        "node":             "generate_response",
        "timestamp":        ts,
        "response_preview": final_response[:120] + ("…" if len(final_response) > 120 else ""),
    }

    return {
        "final_response": final_response,
        "trace": state.get("trace", []) + [trace_entry],
    }
