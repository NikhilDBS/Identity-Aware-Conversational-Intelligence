"""
One-time database reset for the single-user system.

Wipes ALL nodes and relationships, then recreates the schema constraints
and indexes via init_schema.

Usage:
    cd backend
    python scripts/reset_db.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from neo4j import GraphDatabase

NEO4J_URI      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")


def main() -> None:
    print(f"Connecting to {NEO4J_URI} as {NEO4J_USERNAME} ...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    driver.verify_connectivity()

    answer = input("Wipe ALL nodes and relationships? Type YES to confirm: ").strip()
    if answer != "YES":
        print("Aborted — nothing was deleted.")
        driver.close()
        return

    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run("MATCH (n) DETACH DELETE n")
        summary = result.consume()
        print(f"Deleted {summary.counters.nodes_deleted} nodes, "
              f"{summary.counters.relationships_deleted} relationships.")
    driver.close()

    print("\nRe-creating schema …")
    from scripts.init_schema import main as init_main
    init_main()


if __name__ == "__main__":
    main()
