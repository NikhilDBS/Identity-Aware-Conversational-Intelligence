# IACI — Identity-Aware Conversational Intelligence

A conversational agent with persistent, structured memory backed by Neo4j. It remembers who you are, what you've discussed, and how you feel — across conversations.

## Quick Start

### 1. Environment Setup

```bash
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY and other settings
```

### 2. Start Backend + Neo4j

```bash
docker-compose up --build
```

This starts:
- **Neo4j** on `bolt://localhost:7687` (web UI at `http://localhost:7474`)
- **FastAPI** API on `http://localhost:8000`

### 3. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` to chat.

## API Endpoints

| Method | Path | Body/Response | Description |
|--------|------|---------------|-------------|
| POST | `/chat` | `{user_id, message}` → `{reply}` | Send a message, get a memory-grounded reply |
| GET | `/memory/{user_id}` | → JSON dump of identity/episodic/emotional nodes | Debug/demo endpoint |
| GET | `/health` | → `{status: "ok"}` | Health check |

## Architecture — 7-Step Pipeline

Every user message goes through this pipeline:

1. **Ingest** — Receive message + user_id via `/chat`.
2. **Context Reasoning (CoT)** — An LLM reasons (hidden scratchpad) about whether the message needs prior memory, what topic it relates to, and whether it contains memory-worthy content.
3. **Pre-response Retrieval** — If needed, query Neo4j for relevant Identity, Episode, and Emotion nodes filtered by user_id + topic + recency.
4. **Categorize** — A structured-output LLM chain extracts typed memory items (IdentityItem, EpisodicItem, EmotionalItem) using Pydantic schemas passed as tool definitions — not regex or free text.
5. **Store** — Write items to Neo4j following upsert rules (identity overwrites value, keeps history) and append-only rules (episodes, emotions).
6. **Post-store Retrieval** — If new memories connect to older context, run one more targeted query.
7. **Compose Response** — Generate the final reply using message + all retrieved context, with tone calibrated by emotional patterns.

## Graph Schema

```
(:User {user_id})
  -[:HAS_IDENTITY]->(:IdentityFact {id, type, value, previous_value, confidence, first_stated_at, last_confirmed_at, source_msg_id})
  -[:EXPERIENCED]->(:Episode {id, summary, timestamp, topic, entities, source_msg_id})

(:Episode|IdentityFact)
  -[:EVOKED {emotion, intensity, valence, timestamp}]->(:EmotionTag {id, label})

(:Episode)-[:INVOLVES]->(:IdentityFact)
```

### Memory Types

| Type | Behavior | Example |
|------|----------|---------|
| **Identity** | Upserted — new value overwrites old, old stored as `previous_value` | "I'm a nurse" → occupation = nurse |
| **Episodic** | Append-only timestamped events | "Night shift was brutal last night" |
| **Emotional** | Append-only feelings linked to episodes/identity | frustration(0.8) linked to night shift episode |

Emotional trends are computed at query time via aggregation, not stored as running values.

## Neo4j MCP Server

The spec calls for using the official `mcp-neo4j-cypher` MCP server. In this implementation, I made the following engineering decision:

**Decision**: Use the Neo4j Python driver directly instead of running a separate MCP server process. The `mcp-neo4j-cypher` server is designed for MCP client integrations (e.g., Claude Desktop), not for a Python backend that already has a direct driver connection. Running the MCP server as a sidecar adds unnecessary latency and complexity when the Python driver provides the same Cypher execution capabilities. The code is structured so that swapping in MCP tool calls would require changes only in `memory/retrieval.py` and `memory/store.py`.

## Categorization Decisions

- Messages with substantive facts about the user (job, location, preferences) → Identity extraction
- Messages describing events, conversations, or specific occurrences → Episodic extraction  
- Messages expressing feelings, stress, excitement, frustration → Emotional extraction with intensity/valence
- Casual greetings with no substance → No extraction (all arrays empty)

## Assumptions & Decisions

1. **LLM Model**: Default `claude-sonnet-4-6`, configurable via `MODEL_NAME` env var.
2. **Neo4j auth**: Default password `password` in docker-compose, overridable via `.env`.
3. **No MCP sidecar**: Direct driver used for simplicity (see above).
4. **Frontend**: Minimal dark-themed React UI with Tailwind-like CSS (no framework dependency beyond React).
5. **Tests**: Unit tests require a running Neo4j instance (bolt://localhost:7687). Mock the LLM calls, test real DB operations for store/retrieve.
6. **History**: The pipeline accepts optional chat history but the endpoint doesn't persist it — each call is stateless except for Neo4j memory.
