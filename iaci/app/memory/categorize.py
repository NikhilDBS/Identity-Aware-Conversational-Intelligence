from pydantic import BaseModel, Field
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.config import settings


class IdentityItem(BaseModel):
    type: str = Field(description="Category: name, occupation, location, relationship, preference, trait, goal")
    value: str = Field(description="The fact value")
    confidence: float = Field(ge=0, le=1, default=0.9)


class EpisodicItem(BaseModel):
    summary: str = Field(description="Brief summary of the event/what was said")
    topic: str = Field(description="Main topic")
    entities: list[str] = Field(default_factory=list)


class EmotionalItem(BaseModel):
    label: str = Field(description="Emotion label like joy, sadness, frustration, etc")
    intensity: float = Field(ge=0, le=1)
    valence: float = Field(ge=-1, le=1)
    linked_type: str = Field(description="'identity' or 'episodic'")
    linked_index: int = Field(description="Index of the linked item in the same extraction batch, or -1 if none")


class ExtractionResult(BaseModel):
    identity_items: list[IdentityItem] = Field(default_factory=list)
    episodic_items: list[EpisodicItem] = Field(default_factory=list)
    emotional_items: list[EmotionalItem] = Field(default_factory=list)


EXTRACTION_SYSTEM = """You are a memory extraction system. Given a user message, extract structured memory items.

Rules:
- Identity items: stable facts about the user (name, job, location, relationships, preferences, traits, goals)
- Episodic items: specific events or things that happened or were said
- Emotional items: feelings/affect expressed or implied. linked_index refers to the item in this batch it relates to (-1 if standalone).
- Only extract items you are confident about. Return empty arrays if nothing worth remembering.
- Do NOT extract casual small talk with no substance."""


def extract_memories(message: str) -> ExtractionResult:
    llm = ChatMistralAI(model=settings.model_name, mistral_api_key=settings.mistral_api_key, temperature=0)
    structured_llm = llm.with_structured_output(ExtractionResult)
    msgs = [SystemMessage(content=EXTRACTION_SYSTEM), HumanMessage(content=message)]
    return structured_llm.invoke(msgs)
