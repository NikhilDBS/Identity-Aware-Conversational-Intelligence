"""
Parameterized Cypher templates for reading and writing each memory type.

Design principle (per project brief):
  Prefer a small library of fixed templates keyed by category over having
  the LLM generate free-form Cypher — this keeps the graph schema consistent
  and makes debugging straightforward.

All write templates use MERGE on the node id so reruns are idempotent.
"""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any

# ── READ templates ─────────────────────────────────────────────────────────────

READ_RECENT_CONVERSATIONS = """
MATCH (u:User {id: $user_id})-[:HAS_CONVERSATION]->(c:Conversation)-[:CONTAINS]->(m:Message)
WHERE m.role = 'user'
RETURN m.content AS content, m.timestamp AS timestamp, c.id AS conversation_id
ORDER BY m.timestamp DESC
LIMIT $limit
"""

READ_IDENTITY_MEMORIES = """
MATCH (u:User {id: $user_id})-[:HAS_IDENTITY]->(im:IdentityMemory)
WHERE toLower(im.content) CONTAINS toLower($keyword)
   OR im.category = $category
RETURN im.id AS id, im.content AS content, im.category AS category,
       im.confidence AS confidence, im.updated_at AS updated_at
ORDER BY im.confidence DESC, im.updated_at DESC
LIMIT $limit
"""

READ_ALL_IDENTITY_MEMORIES = """
MATCH (u:User {id: $user_id})-[:HAS_IDENTITY]->(im:IdentityMemory)
RETURN im.id AS id, im.content AS content, im.category AS category,
       im.confidence AS confidence, im.updated_at AS updated_at
ORDER BY im.confidence DESC
LIMIT $limit
"""

READ_EPISODIC_MEMORIES = """
MATCH (u:User {id: $user_id})-[:EXPERIENCED]->(em:EpisodicMemory)
WHERE toLower(em.content) CONTAINS toLower($keyword)
   OR toLower(em.event_type) CONTAINS toLower($keyword)
RETURN em.id AS id, em.content AS content, em.event_type AS event_type,
       em.occurred_at AS occurred_at, em.location AS location,
       em.participants AS participants
ORDER BY em.occurred_at DESC
LIMIT $limit
"""

READ_EMOTIONAL_MEMORIES = """
MATCH (u:User {id: $user_id})-[:FELT]->(em:EmotionalMemory)
WHERE toLower(em.trigger) CONTAINS toLower($keyword)
   OR toLower(em.content) CONTAINS toLower($keyword)
RETURN em.id AS id, em.content AS content, em.emotion_label AS emotion_label,
       em.intensity AS intensity, em.valence AS valence,
       em.trigger AS trigger, em.occurred_at AS occurred_at
ORDER BY em.intensity DESC
LIMIT $limit
"""

READ_ALL_EPISODIC_MEMORIES = """
MATCH (u:User {id: $user_id})-[:EXPERIENCED]->(em:EpisodicMemory)
RETURN em.id AS id, em.content AS content, em.event_type AS event_type,
       em.occurred_at AS occurred_at, em.location AS location,
       em.participants AS participants
ORDER BY em.occurred_at DESC
LIMIT $limit
"""

READ_ALL_EMOTIONAL_MEMORIES = """
MATCH (u:User {id: $user_id})-[:FELT]->(em:EmotionalMemory)
RETURN em.id AS id, em.content AS content, em.emotion_label AS emotion_label,
       em.intensity AS intensity, em.valence AS valence,
       em.trigger AS trigger, em.occurred_at AS occurred_at
ORDER BY em.intensity DESC
LIMIT $limit
"""

READ_ALL_USER_MEMORIES = """
MATCH (u:User {id: $user_id})
OPTIONAL MATCH (u)-[:HAS_IDENTITY]->(im:IdentityMemory)
OPTIONAL MATCH (u)-[:EXPERIENCED]->(ep:EpisodicMemory)
OPTIONAL MATCH (u)-[:FELT]->(emo:EmotionalMemory)
RETURN
  collect(DISTINCT {type: 'identity',  data: im})  AS identity_memories,
  collect(DISTINCT {type: 'episodic',  data: ep})  AS episodic_memories,
  collect(DISTINCT {type: 'emotional', data: emo}) AS emotional_memories
"""

# ── WRITE templates ────────────────────────────────────────────────────────────

WRITE_USER_AND_CONVERSATION = """
MERGE (u:User {id: $user_id})
ON CREATE SET u.name = $user_id, u.created_at = $now

MERGE (c:Conversation {id: $conversation_id})
ON CREATE SET c.started_at = $now

MERGE (u)-[:HAS_CONVERSATION]->(c)
"""

WRITE_MESSAGE = """
MERGE (m:Message {id: $message_id})
ON CREATE SET
  m.role      = $role,
  m.content   = $content,
  m.timestamp = $timestamp

WITH m
MATCH (c:Conversation {id: $conversation_id})
MERGE (c)-[:CONTAINS]->(m)
"""

WRITE_IDENTITY_MEMORY = """
MERGE (im:IdentityMemory {id: $memory_id})
ON CREATE SET
  im.content    = $content,
  im.category   = $category,
  im.confidence = $confidence,
  im.created_at = $now,
  im.updated_at = $now
ON MATCH SET
  im.content    = $content,
  im.confidence = $confidence,
  im.updated_at = $now

WITH im
MATCH (u:User {id: $user_id})
MERGE (u)-[:HAS_IDENTITY]->(im)

WITH im
MATCH (m:Message {id: $message_id})
MERGE (m)-[:PRODUCED]->(im)
"""

WRITE_EPISODIC_MEMORY = """
MERGE (ep:EpisodicMemory {id: $memory_id})
ON CREATE SET
  ep.content      = $content,
  ep.event_type   = $event_type,
  ep.occurred_at  = $occurred_at,
  ep.location     = $location,
  ep.participants = $participants

WITH ep
MATCH (u:User {id: $user_id})
MERGE (u)-[:EXPERIENCED]->(ep)

WITH ep
MATCH (m:Message {id: $message_id})
MERGE (m)-[:PRODUCED]->(ep)
"""

WRITE_EMOTIONAL_MEMORY = """
MERGE (emo:EmotionalMemory {id: $memory_id})
ON CREATE SET
  emo.content       = $content,
  emo.emotion_label = $emotion_label,
  emo.intensity     = $intensity,
  emo.valence       = $valence,
  emo.trigger       = $trigger,
  emo.occurred_at   = $now

WITH emo
MATCH (u:User {id: $user_id})
MERGE (u)-[:FELT]->(emo)

WITH emo
MATCH (m:Message {id: $message_id})
MERGE (m)-[:PRODUCED]->(emo)
"""

LINK_EPISODIC_TO_EMOTIONAL = """
MATCH (ep:EpisodicMemory {id: $episodic_id})
MATCH (emo:EmotionalMemory {id: $emotional_id})
MERGE (ep)-[:EVOKED]->(emo)
"""


# ── Helper to build read parameters by intent ─────────────────────────────────

def build_read_params(
    user_id: str,
    keyword: str,
    memory_type: str,
    limit: int = 10,
) -> tuple[str, dict[str, Any]]:
    """
    Return (cypher_query, params) for the given memory_type and keyword.
    Falls back to ALL_* variant when keyword is empty or a generic "all" query.
    """
    kw = keyword.strip() or ""
    base: dict[str, Any] = {"user_id": user_id, "limit": limit}
    is_broad = not kw or kw.lower().split()[0] in ("all", "every", "any")

    if memory_type == "identity":
        if is_broad:
            return READ_ALL_IDENTITY_MEMORIES, base
        return READ_IDENTITY_MEMORIES, {**base, "keyword": kw, "category": kw}
    elif memory_type == "episodic":
        if is_broad:
            return READ_ALL_EPISODIC_MEMORIES, base
        return READ_EPISODIC_MEMORIES, {**base, "keyword": kw}
    elif memory_type == "emotional":
        if is_broad:
            return READ_ALL_EMOTIONAL_MEMORIES, base
        return READ_EMOTIONAL_MEMORIES, {**base, "keyword": kw}
    else:
        return READ_RECENT_CONVERSATIONS, {**base, "limit": 5}


def build_write_params(
    user_id: str,
    message_id: str,
    memory_type: str,
    payload: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """
    Return (cypher_query, params) for the given memory_type and payload dict.
    Generates a stable UUID for the memory node based on content hash.
    """
    now = datetime.utcnow().isoformat()
    memory_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{user_id}:{memory_type}:{payload.get('content', '')}"))

    if memory_type == "identity":
        return WRITE_IDENTITY_MEMORY, {
            "memory_id":  memory_id,
            "user_id":    user_id,
            "message_id": message_id,
            "content":    payload["content"],
            "category":   payload.get("category", "trait"),
            "confidence": payload.get("confidence", 0.8),
            "now":        now,
        }
    elif memory_type == "episodic":
        return WRITE_EPISODIC_MEMORY, {
            "memory_id":    memory_id,
            "user_id":      user_id,
            "message_id":   message_id,
            "content":      payload["content"],
            "event_type":   payload.get("event_type", "event"),
            "occurred_at":  payload.get("occurred_at", now),
            "location":     payload.get("location", ""),
            "participants": payload.get("participants", []),
        }
    elif memory_type == "emotional":
        return WRITE_EMOTIONAL_MEMORY, {
            "memory_id":     memory_id,
            "user_id":       user_id,
            "message_id":    message_id,
            "content":       payload["content"],
            "emotion_label": payload.get("emotion_label", "unknown"),
            "intensity":     payload.get("intensity", 0.5),
            "valence":       payload.get("valence", "neutral"),
            "trigger":       payload.get("trigger", ""),
            "now":           now,
        }
    else:
        raise ValueError(f"Unknown memory_type: {memory_type}")
