import uuid
import logging
from neo4j import Driver
from app.chains.cot_reasoning import reason_about_message
from app.memory.categorize import extract_memories
from app.memory.retrieval import retrieve_context
from app.memory.store import store_memories
from app.chains.response import compose_response

logger = logging.getLogger(__name__)


def run_pipeline(driver: Driver, user_id: str, message: str, history: list[dict] | None = None) -> str:
    msg_id = str(uuid.uuid4())

    reasoning = reason_about_message(message)
    logger.info(f"CoT reasoning: {reasoning}")

    context = {}
    if reasoning.get("needs_memory", True):
        context = retrieve_context(driver, user_id, topic=reasoning.get("likely_topic"))
        logger.info(f"Pre-response context: {context}")

    extraction = None
    if reasoning.get("memory_worthy", True):
        extraction = extract_memories(message)
        logger.info(f"Extraction: identity={len(extraction.identity_items)}, episodic={len(extraction.episodic_items)}, emotional={len(extraction.emotional_items)}")
        store_memories(driver, user_id, extraction, msg_id)

        if extraction.episodic_items or extraction.identity_items:
            extra = retrieve_context(driver, user_id, topic=reasoning.get("likely_topic"))
            for k, v in extra.items():
                if k not in context or not context[k]:
                    context[k] = v

    reply = compose_response(message, context, history)
    return reply
