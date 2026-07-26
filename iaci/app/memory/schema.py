from neo4j import Driver

CONSTRAINTS = [
    "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE",
    "CREATE CONSTRAINT identity_id IF NOT EXISTS FOR (i:IdentityFact) REQUIRE i.id IS UNIQUE",
    "CREATE CONSTRAINT episode_id IF NOT EXISTS FOR (e:Episode) REQUIRE e.id IS UNIQUE",
    "CREATE CONSTRAINT emotion_id IF NOT EXISTS FOR (e:EmotionTag) REQUIRE e.id IS UNIQUE",
]


def init_schema(driver: Driver) -> None:
    with driver.session() as session:
        for stmt in CONSTRAINTS:
            session.run(stmt)
