import time
import logging
from neo4j import GraphDatabase, Driver
from app.config import settings

logger = logging.getLogger(__name__)

_driver: Driver | None = None


def get_driver() -> Driver:
    global _driver
    if _driver is None:
        for attempt in range(10):
            try:
                _driver = GraphDatabase.driver(
                    settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
                )
                _driver.verify_connectivity()
                return _driver
            except Exception as e:
                logger.info(f"Neo4j connection attempt {attempt + 1} failed: {e}")
                time.sleep(2)
        raise RuntimeError("Could not connect to Neo4j after 10 attempts")
    return _driver


def close_driver() -> None:
    global _driver
    if _driver:
        _driver.close()
        _driver = None
