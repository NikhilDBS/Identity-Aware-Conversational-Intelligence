"""
One-time schema setup script.
Run this ONCE against your local Neo4j instance before starting the app.

Usage:
    cd backend
    cp .env.example .env   # fill in your NEO4J_PASSWORD
    python scripts/init_schema.py

This uses the official Neo4j Python driver directly (NOT the MCP server),
since schema setup is a one-time admin operation, not a conversational query.
"""
import os
import sys
from pathlib import Path

# Allow running as `python scripts/init_schema.py` from the backend/ directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from neo4j import GraphDatabase

NEO4J_URI      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

CONSTRAINTS = [
    "CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (n:User) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT conversation_id_unique IF NOT EXISTS FOR (n:Conversation) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT message_id_unique IF NOT EXISTS FOR (n:Message) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT identity_memory_id_unique IF NOT EXISTS FOR (n:IdentityMemory) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT episodic_memory_id_unique IF NOT EXISTS FOR (n:EpisodicMemory) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT emotional_memory_id_unique IF NOT EXISTS FOR (n:EmotionalMemory) REQUIRE n.id IS UNIQUE",
]

INDEXES = [
    "CREATE INDEX episodic_occurred_at IF NOT EXISTS FOR (n:EpisodicMemory) ON (n.occurred_at)",
    "CREATE INDEX emotional_trigger IF NOT EXISTS FOR (n:EmotionalMemory) ON (n.trigger)",
    "CREATE INDEX emotional_emotion_label IF NOT EXISTS FOR (n:EmotionalMemory) ON (n.emotion_label)",
    "CREATE INDEX identity_category IF NOT EXISTS FOR (n:IdentityMemory) ON (n.category)",
    "CREATE INDEX message_timestamp IF NOT EXISTS FOR (n:Message) ON (n.timestamp)",
]


def main() -> None:
    if not NEO4J_PASSWORD:
        print("⚠️  NEO4J_PASSWORD is not set in .env — attempting to connect with empty password.")
        print("    If your Neo4j instance has a password, set it in backend/.env first.\n")

    print(f"Connecting to {NEO4J_URI} as {NEO4J_USERNAME} ...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

    try:
        driver.verify_connectivity()
        print("✅ Connection successful.\n")
    except Exception as e:
        print(f"❌ Could not connect to Neo4j: {e}")
        print("   Make sure Neo4j Desktop / Community Server is running and the credentials are correct.")
        sys.exit(1)

    with driver.session(database=NEO4J_DATABASE) as session:
        print("Creating uniqueness constraints …")
        for stmt in CONSTRAINTS:
            try:
                session.run(stmt)
                label = stmt.split("FOR (n:")[1].split(")")[0]
                print(f"  ✅ {label}")
            except Exception as e:
                print(f"  ⚠️  {stmt[:60]}…  → {e}")

        print("\nCreating indexes …")
        for stmt in INDEXES:
            try:
                session.run(stmt)
                desc = stmt.split("FOR (n:")[1].split(" ON")[0]
                print(f"  ✅ {desc}")
            except Exception as e:
                print(f"  ⚠️  {stmt[:60]}…  → {e}")

    driver.close()
    print("\n🎉 Schema initialisation complete. You can now start the backend with:")
    print("   uvicorn app.main:app --reload")


if __name__ == "__main__":
    main()
