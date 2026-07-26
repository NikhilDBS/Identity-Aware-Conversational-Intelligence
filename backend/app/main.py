"""
FastAPI application entry point.

Run with:
    cd backend
    uvicorn app.main:app --reload
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.mcp.client import mcp_manager
from app.api.routes.chat import router as chat_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the MCP server subprocess at startup; shut it down at exit."""
    settings = get_settings()
    logger.info("Starting IACI backend — model: %s", settings.litellm_model)
    logger.info("Neo4j URI: %s  database: %s", settings.neo4j_uri, settings.neo4j_database)

    await mcp_manager.start()
    logger.info("MCP client ready.")

    yield  # ← server is live here

    logger.info("Shutting down …")
    await mcp_manager.stop()


settings = get_settings()

app = FastAPI(
    title="Identity-Aware Conversational Intelligence",
    description=(
        "A conversational agent with three structured memory types "
        "(identity, episodic, emotional) backed by Neo4j."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS — allow the Vite dev server and any local origin ─────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(chat_router, prefix="/api", tags=["chat"])


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "model":  settings.litellm_model,
        "neo4j":  settings.neo4j_uri,
        "mcp_tools": [t.name for t in mcp_manager.get_tools()],
    }
