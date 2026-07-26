"""
Node 3: extract_and_classify
─────────────────────────────
Chain-of-thought LLM call that extracts zero or more memory items from the
user's message and classifies each as identity / episodic / emotional with
full structured metadata.

Empty list is the expected output for small talk and clarifying questions.
Uses LiteLLM's acompletion with json_object response_format.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import litellm

from app.core.config import get_settings
from app.graph.state import PipelineState
from app.models.schemas import MemoryExtractionResult

logger = logging.getLogger(__name__)

litellm.suppress_debug_info = True


SYSTEM_PROMPT = """You are the memory extraction module for a conversational AI.

Given a user message and any retrieved context, extract ALL facts, events, and emotional states
worth storing as long-term memories. Classify each into exactly one of:

  • identity  — a durable fact about WHO the user is (trait, preference, value, role, relationship, goal)
  • episodic  — a specific event/experience with a WHEN and WHAT HAPPENED
  • emotional — an affective state tied to a trigger (topic, event, or person)

Rules:
- A single message can produce zero, one, or MULTIPLE memories across different types.
- "I bombed my interview today and I'm scared" → 1 episodic (interview) + 1 emotional (scared)
- Do NOT extract trivial statements, greetings, or questions as memories.
- Do NOT duplicate what is already in retrieved_context (unless updating it with new info).
- For emotional items: intensity 0.0–1.0, valence ∈ {positive, negative, neutral, mixed}.
- For episodic items: occurred_at should be ISO date if determinable, or a relative description.
- For identity items: confidence 0.0–1.0.
- If nothing is worth storing, return an empty memories list — this is FINE and expected.

Return ONLY valid JSON matching this exact schema:
{
  "memories": [
    {
      "memory_type": "identity" | "episodic" | "emotional",
      "identity": {   // only when memory_type == "identity"
        "content": "...",
        "category": "trait" | "preference" | "value" | "role" | "relationship" | "goal",
        "confidence": 0.0-1.0
      },
      "episodic": {   // only when memory_type == "episodic"
        "content": "...",
        "event_type": "...",
        "occurred_at": "...",
        "location": null,
        "participants": []
      },
      "emotional": {  // only when memory_type == "emotional"
        "content": "...",
        "emotion_label": "...",
        "intensity": 0.0-1.0,
        "valence": "positive" | "negative" | "neutral" | "mixed",
        "trigger": "..."
      }
    }
  ],
  "reasoning": "..."
}
"""


def _format_context(retrieved_context: list[dict]) -> str:
    if not retrieved_context:
        return "(no prior context retrieved)"
    lines = []
    for item in retrieved_context:
        lines.append(f"[{item.get('memory_type', '?')} / {item.get('intent', '')}]")
        for row in item.get("results", [])[:3]:
            lines.append(f"  • {row}")
    return "\n".join(lines)


async def extract_and_classify(state: PipelineState) -> dict[str, Any]:
    settings = get_settings()
    ts = datetime.utcnow().isoformat()

    context_text = _format_context(state.get("retrieved_context", []))

    user_prompt = f"""Retrieved context:
{context_text}

User message:
\"{state['user_message']}\"

Extract all memory-worthy items and return the JSON."""

    try:
        response = await litellm.acompletion(
            model=settings.litellm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        raw_json = response.choices[0].message.content
        data = json.loads(raw_json)
        result = MemoryExtractionResult.model_validate(data)
        logger.info("extract_and_classify: %d memories found", len(result.memories))
    except Exception as exc:
        logger.error("extract_and_classify failed: %s", exc)
        result = MemoryExtractionResult(memories=[], reasoning=f"Extraction failed: {exc}")

    # Serialize memories to plain dicts for the state
    serialized: list[dict[str, Any]] = []
    for mem in result.memories:
        entry: dict[str, Any] = {"memory_type": mem.memory_type.value}
        if mem.memory_type.value == "identity" and mem.identity:
            entry.update(mem.identity.model_dump())
        elif mem.memory_type.value == "episodic" and mem.episodic:
            entry.update(mem.episodic.model_dump())
        elif mem.memory_type.value == "emotional" and mem.emotional:
            entry.update(mem.emotional.model_dump())
        serialized.append(entry)

    trace_entry = {
        "node":           "extract_and_classify",
        "timestamp":      ts,
        "memories_found": len(serialized),
        "breakdown": {
            "identity":  sum(1 for m in serialized if m["memory_type"] == "identity"),
            "episodic":  sum(1 for m in serialized if m["memory_type"] == "episodic"),
            "emotional": sum(1 for m in serialized if m["memory_type"] == "emotional"),
        },
        "reasoning": result.reasoning,
        "memories":  serialized,
    }

    return {
        "extracted_memories": serialized,
        "trace": state.get("trace", []) + [trace_entry],
    }
