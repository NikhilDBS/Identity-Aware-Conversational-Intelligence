from neo4j import Driver


def retrieve_identity(driver: Driver, user_id: str) -> list[dict]:
    with driver.session() as session:
        result = session.run(
            """
            MATCH (u:User {user_id: $uid})-[:HAS_IDENTITY]->(i:IdentityFact)
            RETURN i.type AS type, i.value AS value, i.confidence AS confidence,
                   i.last_confirmed_at AS last_confirmed
            ORDER BY i.last_confirmed_at DESC LIMIT 50
            """,
            uid=user_id,
        )
        return [dict(r) for r in result]


def retrieve_episodes(driver: Driver, user_id: str, topic: str | None = None, limit: int = 10) -> list[dict]:
    params: dict = {"uid": user_id, "limit": limit}
    if topic:
        query = """
            MATCH (u:User {user_id: $uid})-[:EXPERIENCED]->(e:Episode)
            WHERE e.topic = $topic
            RETURN e.id AS id, e.summary AS summary, e.timestamp AS timestamp,
                   e.topic AS topic, e.entities AS entities
            ORDER BY e.timestamp DESC LIMIT $limit
        """
        params["topic"] = topic
    else:
        query = """
            MATCH (u:User {user_id: $uid})-[:EXPERIENCED]->(e:Episode)
            RETURN e.id AS id, e.summary AS summary, e.timestamp AS timestamp,
                   e.topic AS topic, e.entities AS entities
            ORDER BY e.timestamp DESC LIMIT $limit
        """
    with driver.session() as session:
        result = session.run(query, **params)
        return [dict(r) for r in result]


def retrieve_emotions(driver: Driver, user_id: str, topic: str | None = None, limit: int = 20) -> list[dict]:
    with driver.session() as session:
        result = session.run(
            """
            MATCH (u:User {user_id: $uid})-[:EXPERIENCED]->(e:Episode)-[r:EVOKED]->(et:EmotionTag)
            RETURN et.label AS emotion, r.intensity AS intensity, r.valence AS valence,
                   r.timestamp AS timestamp, e.topic AS topic
            ORDER BY r.timestamp DESC LIMIT $limit
            """,
            uid=user_id, limit=limit,
        )
        ep_emotions = [dict(r) for r in result]
        result2 = session.run(
            """
            MATCH (u:User {user_id: $uid})-[:HAS_IDENTITY]->(i:IdentityFact)-[r:EVOKED]->(et:EmotionTag)
            RETURN et.label AS emotion, r.intensity AS intensity, r.valence AS valence,
                   r.timestamp AS timestamp, i.type AS topic
            ORDER BY r.timestamp DESC LIMIT $limit
            """,
            uid=user_id, limit=limit,
        )
        id_emotions = [dict(r) for r in result2]
    seen = set()
    merged = []
    for e in ep_emotions + id_emotions:
        key = (e.get("emotion"), e.get("timestamp"))
        if key not in seen:
            seen.add(key)
            merged.append(e)
    return merged[:limit]


def aggregate_emotional_trends(driver: Driver, user_id: str) -> list[dict]:
    with driver.session() as session:
        result = session.run(
            """
            MATCH (u:User {user_id: $uid})-[:EXPERIENCED]->(e:Episode)-[r:EVOKED]->(et:EmotionTag)
            RETURN et.label AS emotion, avg(r.intensity) AS avg_intensity,
                   avg(r.valence) AS avg_valence, count(*) AS count
            UNION
            MATCH (u:User {user_id: $uid})-[:HAS_IDENTITY]->(i:IdentityFact)-[r:EVOKED]->(et:EmotionTag)
            RETURN et.label AS emotion, avg(r.intensity) AS avg_intensity,
                   avg(r.valence) AS avg_valence, count(*) AS count
            """,
            uid=user_id,
        )
        rows = [dict(r) for r in result]
    merged: dict[str, dict] = {}
    for r in rows:
        label = r["emotion"]
        if label in merged:
            existing = merged[label]
            total = existing["count"] + r["count"]
            existing["avg_intensity"] = (existing["avg_intensity"] * existing["count"] + r["avg_intensity"] * r["count"]) / total
            existing["avg_valence"] = (existing["avg_valence"] * existing["count"] + r["avg_valence"] * r["count"]) / total
            existing["count"] = total
        else:
            merged[label] = dict(r)
    return sorted(merged.values(), key=lambda x: x["count"], reverse=True)


def retrieve_context(driver: Driver, user_id: str, topic: str | None = None) -> dict:
    return {
        "identity": retrieve_identity(driver, user_id),
        "episodes": retrieve_episodes(driver, user_id, topic),
        "emotions": retrieve_emotions(driver, user_id, topic),
        "emotional_trends": aggregate_emotional_trends(driver, user_id),
    }
