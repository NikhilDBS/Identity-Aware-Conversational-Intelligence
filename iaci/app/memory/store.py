import uuid
import logging
from datetime import datetime, timezone
from neo4j import Driver
from app.memory.categorize import ExtractionResult

logger = logging.getLogger(__name__)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid() -> str:
    return str(uuid.uuid4())


def store_identity(driver: Driver, user_id: str, item, msg_id: str) -> str | None:
    node_id = _uid()
    ts = _ts()
    with driver.session() as session:
        session.run("MERGE (u:User {user_id: $uid})", uid=user_id)
        existing = session.run(
            "MATCH (u:User {user_id: $uid})-[:HAS_IDENTITY]->(i:IdentityFact {type: $type}) "
            "RETURN i.id AS id, i.value AS value",
            uid=user_id, type=item.type,
        )
        rec = existing.single()
        if rec:
            prev_val = rec["value"]
            session.run(
                "MATCH (i:IdentityFact {id: $id}) "
                "SET i.previous_value = $prev, i.value = $val, "
                "    i.confidence = $conf, i.last_confirmed_at = $ts, i.source_msg_id = $mid",
                id=rec["id"], prev=prev_val, val=item.value, conf=item.confidence, ts=ts, mid=msg_id,
            )
            return rec["id"]
        else:
            session.run(
                "MATCH (u:User {user_id: $uid}) "
                "CREATE (u)-[:HAS_IDENTITY]->(i:IdentityFact {"
                "  id: $id, type: $type, value: $val, previous_value: null, "
                "  confidence: $conf, first_stated_at: $ts, last_confirmed_at: $ts, source_msg_id: $mid"
                "})",
                uid=user_id, id=node_id, type=item.type, val=item.value,
                conf=item.confidence, ts=ts, mid=msg_id,
            )
            return node_id


def store_episode(driver: Driver, user_id: str, item, msg_id: str) -> str:
    node_id = _uid()
    ts = _ts()
    with driver.session() as session:
        session.run("MERGE (u:User {user_id: $uid})", uid=user_id)
        session.run(
            "MATCH (u:User {user_id: $uid}) "
            "CREATE (u)-[:EXPERIENCED]->(e:Episode {"
            "  id: $id, summary: $sum, timestamp: $ts, topic: $topic, "
            "  entities: $ents, source_msg_id: $mid"
            "})",
            uid=user_id, id=node_id, sum=item.summary, ts=ts,
            topic=item.topic, ents=item.entities, mid=msg_id,
        )
    return node_id


def store_emotion(driver: Driver, user_id: str, item, episode_ids: list[str], identity_ids: list[str]) -> str:
    node_id = _uid()
    ts = _ts()
    with driver.session() as session:
        session.run(
            "CREATE (et:EmotionTag {id: $id, label: $label})",
            id=node_id, label=item.label,
        )
        if item.linked_type == "episodic" and 0 <= item.linked_index < len(episode_ids):
            eid = episode_ids[item.linked_index]
            session.run(
                "MATCH (e:Episode {id: $eid}) MATCH (et:EmotionTag {id: $etid}) "
                "CREATE (e)-[:EVOKED {emotion: $em, intensity: $int, valence: $val, timestamp: $ts}]->(et)",
                eid=eid, etid=node_id, em=item.label, int=item.intensity, val=item.valence, ts=ts,
            )
        elif item.linked_type == "identity" and 0 <= item.linked_index < len(identity_ids):
            iid = identity_ids[item.linked_index]
            session.run(
                "MATCH (i:IdentityFact {id: $iid}) MATCH (et:EmotionTag {id: $etid}) "
                "CREATE (i)-[:EVOKED {emotion: $em, intensity: $int, valence: $val, timestamp: $ts}]->(et)",
                iid=iid, etid=node_id, em=item.label, int=item.intensity, val=item.valence, ts=ts,
            )
    return node_id


def store_memories(driver: Driver, user_id: str, extraction: ExtractionResult, msg_id: str) -> None:
    episode_ids: list[str] = []
    identity_ids: list[str] = []
    for item in extraction.identity_items:
        try:
            iid = store_identity(driver, user_id, item, msg_id)
            if iid:
                identity_ids.append(iid)
        except Exception as e:
            logger.error(f"Failed to store identity: {e}")
    for item in extraction.episodic_items:
        try:
            eid = store_episode(driver, user_id, item, msg_id)
            episode_ids.append(eid)
        except Exception as e:
            logger.error(f"Failed to store episode: {e}")
    for item in extraction.emotional_items:
        try:
            store_emotion(driver, user_id, item, episode_ids, identity_ids)
        except Exception as e:
            logger.error(f"Failed to store emotion: {e}")
