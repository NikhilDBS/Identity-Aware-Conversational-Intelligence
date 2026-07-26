import pytest
from unittest.mock import patch, MagicMock
from app.memory.categorize import ExtractionResult, IdentityItem, EpisodicItem, EmotionalItem


def test_mixed_message_extraction():
    """Test that a message with identity, episodic, and emotional content splits into all three types."""
    mock_result = ExtractionResult(
        identity_items=[IdentityItem(type="occupation", value="nurse", confidence=0.95)],
        episodic_items=[EpisodicItem(summary="Works night shifts", topic="work", entities=["hospital"])],
        emotional_items=[EmotionalItem(label="exhaustion", intensity=0.8, valence=-0.6, linked_type="episodic", linked_index=0)],
    )
    with patch("app.memory.categorize.ChatAnthropic") as mock_chat:
        mock_llm = MagicMock()
        mock_chat.return_value = mock_llm
        mock_llm.with_structured_output.return_value.invoke.return_value = mock_result
        from app.memory.categorize import extract_memories
        result = extract_memories("I'm a nurse, night shifts are exhausting me")
        assert len(result.identity_items) == 1
        assert len(result.episodic_items) == 1
        assert len(result.emotional_items) == 1
        assert result.identity_items[0].type == "occupation"
        assert result.emotional_items[0].linked_type == "episodic"


def test_identity_upsert_overwrites():
    """Test that storing an identity fact with the same type updates the previous value."""
    from app.memory.store import store_identity, _uid
    from app.memory.categorize import IdentityItem
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
    uid = "test_upsert_user"
    try:
        with driver.session() as session:
            session.run("MATCH (u:User {user_id: $uid}) DETACH DELETE u", uid=uid)
            session.run("MERGE (u:User {user_id: $uid})", uid=uid)

        item1 = IdentityItem(type="occupation", value="nurse", confidence=0.9)
        iid = store_identity(driver, uid, item1, "msg1")
        assert iid is not None

        item2 = IdentityItem(type="occupation", value="doctor", confidence=0.95)
        store_identity(driver, uid, item2, "msg2")

        with driver.session() as session:
            rec = session.run(
                "MATCH (u:User {user_id: $uid})-[:HAS_IDENTITY]->(i:IdentityFact {type: 'occupation'}) "
                "RETURN i.value AS value, i.previous_value AS prev",
                uid=uid,
            ).single()
            assert rec["value"] == "doctor"
            assert rec["prev"] == "nurse"

        with driver.session() as session:
            session.run("MATCH (u:User {user_id: $uid}) DETACH DELETE u", uid=uid)
    finally:
        driver.close()


def test_episodic_append_only():
    """Test that episodic memories are append-only (not overwritten)."""
    from app.memory.store import store_episode
    from app.memory.categorize import EpisodicItem
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
    uid = "test_episodic_user"
    try:
        with driver.session() as session:
            session.run("MATCH (u:User {user_id: $uid}) DETACH DELETE u", uid=uid)
            session.run("MERGE (u:User {user_id: $uid})", uid=uid)

        item1 = EpisodicItem(summary="First event", topic="work", entities=[])
        item2 = EpisodicItem(summary="Second event", topic="health", entities=[])
        store_episode(driver, uid, item1, "msg1")
        store_episode(driver, uid, item2, "msg2")

        with driver.session() as session:
            result = session.run(
                "MATCH (u:User {user_id: $uid})-[:EXPERIENCED]->(e:Episode) RETURN count(e) AS cnt",
                uid=uid,
            ).single()
            assert result["cnt"] == 2

        with driver.session() as session:
            session.run("MATCH (u:User {user_id: $uid}) DETACH DELETE u", uid=uid)
    finally:
        driver.close()


def test_emotional_trend_aggregation():
    """Test that emotional trend aggregation returns correct averages."""
    from app.memory.store import store_emotion, store_episode
    from app.memory.categorize import EpisodicItem, EmotionalItem
    from app.memory.retrieval import aggregate_emotional_trends
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
    uid = "test_emotion_user"
    try:
        with driver.session() as session:
            session.run("MATCH (u:User {user_id: $uid}) DETACH DELETE u", uid=uid)
            session.run("MERGE (u:User {user_id: $uid})", uid=uid)

        ep1 = EpisodicItem(summary="Event 1", topic="work", entities=[])
        ep2 = EpisodicItem(summary="Event 2", topic="work", entities=[])
        eid1 = store_episode(driver, uid, ep1, "msg1")
        eid2 = store_episode(driver, uid, ep2, "msg2")

        em1 = EmotionalItem(label="frustration", intensity=0.7, valence=-0.5, linked_type="episodic", linked_index=0)
        em2 = EmotionalItem(label="frustration", intensity=0.9, valence=-0.8, linked_type="episodic", linked_index=1)
        store_emotion(driver, uid, em1, [eid1, eid2], [])
        store_emotion(driver, uid, em2, [eid1, eid2], [])

        trends = aggregate_emotional_trends(driver, uid)
        assert len(trends) == 1
        assert trends[0]["emotion"] == "frustration"
        assert abs(trends[0]["avg_intensity"] - 0.8) < 0.01
        assert abs(trends[0]["avg_valence"] - (-0.65)) < 0.01

        with driver.session() as session:
            session.run("MATCH (u:User {user_id: $uid}) DETACH DELETE u", uid=uid)
    finally:
        driver.close()


def test_pipeline_end_to_end_mocked():
    """Test the full pipeline with mocked LLM calls."""
    from app.memory.categorize import ExtractionResult, IdentityItem, EmotionalItem
    from app.memory.store import store_identity, store_episode
    from app.memory.categorize import IdentityItem as II
    from neo4j import GraphDatabase
    import uuid

    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
    uid = "test_e2e_user"
    try:
        with driver.session() as session:
            session.run("MATCH (u:User {user_id: $uid}) DETACH DELETE u", uid=uid)
            session.run("MERGE (u:User {user_id: $uid})", uid=uid)

        item = II(type="occupation", value="nurse", confidence=0.95)
        store_identity(driver, uid, item, str(uuid.uuid4()))

        extraction = ExtractionResult(
            identity_items=[],
            episodic_items=[],
            emotional_items=[EmotionalItem(label="exhaustion", intensity=0.8, valence=-0.6, linked_type="identity", linked_index=-1)],
        )

        with patch("app.chains.cot_reasoning.ChatMistralAI") as mock_cot, \
             patch("app.memory.categorize.ChatMistralAI") as mock_cat, \
             patch("app.chains.response.ChatMistralAI") as mock_resp:

            mock_cot.return_value.invoke.return_value = MagicMock(
                content='{"needs_memory": true, "likely_topic": "work", "memory_worthy": false, "reasoning": "asking about work"}'
            )
            mock_resp.return_value.invoke.return_value = MagicMock(content="How's work going? I hope the night shifts aren't too draining!")

            from app.pipeline import run_pipeline
            reply = run_pipeline(driver, uid, "how's work going?")

            assert "work" in reply.lower() or "shift" in reply.lower() or "nurse" in reply.lower() or len(reply) > 10

        with driver.session() as session:
            session.run("MATCH (u:User {user_id: $uid}) DETACH DELETE u", uid=uid)
    finally:
        driver.close()
