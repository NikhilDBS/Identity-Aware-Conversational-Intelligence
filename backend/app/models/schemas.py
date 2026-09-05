"""
All Pydantic models used across the pipeline:
  - Structured LLM outputs (ContextAssessment, MemoryExtractionResult)
  - Memory item types (IdentityItem, EpisodicItem, EmotionalItem)
  - FastAPI request / response bodies
"""
from __future__ import annotations

from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime


# ── Enums ─────────────────────────────────────────────────────────────────────

class IdentityCategory(str, Enum):
    trait        = "trait"
    preference   = "preference"
    value        = "value"
    role         = "role"
    relationship = "relationship"
    goal         = "goal"


class Valence(str, Enum):
    positive = "positive"
    negative = "negative"
    neutral  = "neutral"
    mixed    = "mixed"


class MemoryType(str, Enum):
    identity  = "identity"
    episodic  = "episodic"
    emotional = "emotional"


# ── Structured LLM outputs ────────────────────────────────────────────────────

class RetrievalIntent(BaseModel):
    """A single natural-language retrieval intent, translated into a Cypher query later."""
    description: str = Field(
        description="What to look for, e.g. 'check if user has mentioned job interviews'"
    )
    memory_types: list[MemoryType] = Field(
        description="Which memory type(s) are most likely to contain this information"
    )


class ContextAssessment(BaseModel):
    """Structured output of the assess_context node."""
    needs_retrieval: bool = Field(
        description="True if past memory should be retrieved to properly understand/respond to the message"
    )
    retrieval_intents: list[RetrievalIntent] = Field(
        default_factory=list,
        description="List of retrieval intents (only populated when needs_retrieval is True)"
    )
    reasoning: str = Field(
        description="Brief chain-of-thought: why retrieval is or isn't needed"
    )


class IdentityItem(BaseModel):
    """A durable fact about who the user is."""
    content: str = Field(description="The fact, e.g. 'User is a backend engineer'")
    category: IdentityCategory
    confidence: float = Field(ge=0.0, le=1.0, description="How confident (0-1) this fact is")


class EpisodicItem(BaseModel):
    """A specific event/experience."""
    content: str = Field(description="What happened, e.g. 'User had a job interview'")
    event_type: str = Field(description="Short label like 'job_interview', 'travel', 'social_event'")
    occurred_at: str = Field(
        description="ISO date or relative description like 'today', '2024-07-20', 'last weekend'"
    )
    location: Optional[str] = Field(default=None, description="Where it happened, if mentioned")
    participants: list[str] = Field(
        default_factory=list,
        description="People involved, if mentioned"
    )


class EmotionalItem(BaseModel):
    """An affective state tied to a trigger."""
    content: str = Field(description="The emotional state, e.g. 'User feels anxious about interviews'")
    emotion_label: str = Field(description="Primary emotion: anxious, joyful, sad, proud, etc.")
    intensity: float = Field(ge=0.0, le=1.0, description="Strength of the emotion (0-1)")
    valence: Valence
    trigger: str = Field(description="What triggered this emotion: a topic, event, or person")


class ExtractedMemory(BaseModel):
    """A single extracted memory with its type and payload."""
    memory_type: MemoryType
    identity: Optional[IdentityItem]   = None
    episodic: Optional[EpisodicItem]   = None
    emotional: Optional[EmotionalItem] = None


class MemoryExtractionResult(BaseModel):
    """Structured output of the extract_and_classify node."""
    memories: list[ExtractedMemory] = Field(
        default_factory=list,
        description="Zero or more memories extracted from this message. Empty list is common for small talk."
    )
    reasoning: str = Field(
        description="Chain-of-thought: what was found and why"
    )


# ── FastAPI request / response ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    # Single-user system: no user_id — all memories belong to the one user.
    conversation_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="UUID for the current conversation session"
    )
    message: str = Field(description="The user's message text")


class TraceEntry(BaseModel):
    """One entry in the per-turn debug trace."""
    node: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: dict


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    trace: list[TraceEntry] = Field(default_factory=list)
