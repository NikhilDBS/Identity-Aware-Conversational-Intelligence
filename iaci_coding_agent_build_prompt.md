You are building **IACI (Identity-Aware Conversational Intelligence)** — a
conversational agent with persistent, structured memory backed by Neo4j.
Build the full working system end-to-end: backend, memory pipeline, and a
minimal chat interface to test it. Do not stop for clarification on
ambiguous points — make a reasonable engineering decision, note it in the
README, and keep going.

## GOAL

A chat agent that, on every user turn, retrieves relevant memory from Neo4j,
generates a response grounded in that memory, and extracts/stores new
memories from the turn — split across three types:

1. **Identity memory** — stable facts about the user (name, occupation,
   location, relationships, preferences, traits, goals). Upserted over time
   (conflicts update the value and keep history), not duplicated.
2. **Episodic memory** — specific, timestamped events/things that happened
   or were said. Append-only.
3. **Emotional memory** — feelings/affect tied to an episode, identity fact,
   or topic (emotion label, intensity 0–1, valence -1..1, timestamp).
   Append-only; trends are computed at query time via aggregation, not
   stored as running values.

## TECH STACK

- Python 3.11+
- LangChain (latest) for orchestration and chain-of-thought / tool-calling
- Anthropic Claude as the LLM (use `langchain-anthropic`; read API key from
  `ANTHROPIC_API_KEY` env var; model name configurable via `.env`, default
  `claude-sonnet-4-6`)
- Neo4j as the memory store, accessed via **Neo4j's official MCP server**
  (`mcp-neo4j-cypher` from the `neo4j-contrib/mcp-neo4j` project). Do NOT
  hand-roll an MCP server — install/configure the official package, run it
  as a separate process/container, and wire it into LangChain via its MCP
  adapter (e.g. `langchain-mcp-adapters`) so the LLM calls its
  `read-neo4j-cypher` / `write-neo4j-cypher` tools directly. Pass Neo4j
  connection details to the official server via its documented env vars/CLI
  args — check the package's current README for exact tool names and
  invocation, since interfaces can change between versions.
- FastAPI for the backend HTTP API
- A React frontend (Vite + React, TypeScript) for the chat UI, calling the
  `/chat` endpoint. Apply the **Taste Skill v2** design skill/guidelines for
  visual and interaction design of this frontend — load and follow that
  skill's guidance on layout, typography, color, and component choices
  rather than defaulting to generic/templated UI.
- `docker-compose.yml` that spins up Neo4j (with the APOC plugin) and the
  FastAPI app together
- pytest for tests

## ARCHITECTURE / PIPELINE (implement exactly this flow per user message)

1. **Ingest** — receive user message + session/user_id via `/chat` endpoint.
2. **Context reasoning (CoT)** — use a LangChain prompt/chain that reasons
   (in a hidden scratchpad, not shown to the user) about what the message
   needs: does answering require prior memory? Is there new memory-worthy
   content?
3. **Pre-response retrieval** — if needed, call the Neo4j MCP tool with a
   narrow, parameterized Cypher query (filter by user_id + entity/topic/
   recency, not full-graph scans) to pull relevant Identity/Episodic/
   Emotional nodes.
4. **Categorize** — an LLM extraction chain that reads the user message and
   emits zero or more structured memory items, each tagged with type
   (identity/episodic/emotional), fields, and confidence. A single message
   can yield multiple items across categories. Use structured output
   (function-calling/tool schema, not free text parsing) for this step.
5. **Store** — write each item to Neo4j via the MCP tool following the
   upsert (identity) / append-only (episodic, emotional) rules above. Link
   emotional nodes to the episode/identity node they relate to when
   applicable. Handle write failures gracefully (log, don't block the
   turn).
6. **Post-store retrieval** — if the new memory connects to older context
   not already retrieved, run one more targeted query.
7. **Compose response** — generate the final reply using the original
   message + all retrieved context, with tone calibrated by known emotional
   patterns (not stated clinically/diagnostically to the user). Never leak
   raw Cypher, node IDs, or the internal CoT scratchpad into the response.

## NEO4J SCHEMA (create constraints/indexes on startup)

```cypher
CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE;
CREATE CONSTRAINT identity_id IF NOT EXISTS FOR (i:IdentityFact) REQUIRE i.id IS UNIQUE;
CREATE CONSTRAINT episode_id IF NOT EXISTS FOR (e:Episode) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT emotion_id IF NOT EXISTS FOR (e:EmotionTag) REQUIRE e.id IS UNIQUE;
```

Node/edge shape:

- `(:User {user_id})-[:HAS_IDENTITY]->(:IdentityFact {id, type, value, previous_value, confidence, first_stated_at, last_confirmed_at, source_msg_id})`
- `(:User)-[:EXPERIENCED]->(:Episode {id, summary, timestamp, topic, entities, source_msg_id})`
- `(:Episode|IdentityFact)-[:EVOKED {emotion, intensity, valence, timestamp}]->(:EmotionTag {id, label})`
- Episodes may link to the IdentityFact nodes they reference, e.g.
  `(:Episode)-[:INVOLVES]->(:IdentityFact)`

## PROJECT STRUCTURE

```
iaci/
  app/
    main.py                # FastAPI app, /chat, /health, /memory/{user_id}
    config.py               # env-based settings
    memory/
      schema.py             # Cypher constraint setup
      neo4j_client.py        # MCP client wrapper / direct driver fallback
      retrieval.py           # retrieval query builders
      categorize.py          # structured-output extraction chain
      store.py               # upsert/append write logic
    chains/
      cot_reasoning.py       # step 2 chain
      response.py             # step 7 chain
    pipeline.py              # orchestrates steps 1–7
  frontend/                    # React + Vite + TypeScript chat UI
    src/
      App.tsx
      components/
      styles/
    index.html
    package.json
    vite.config.ts
  tests/
    test_categorize.py
    test_pipeline.py
    test_memory_store.py
  docker-compose.yml
  requirements.txt
  .env.example
  README.md
```

## REQUIREMENTS

- `/chat` endpoint: `POST {user_id, message}` → `{reply}`. Runs the full
  7-step pipeline.
- `/memory/{user_id}` endpoint: `GET` → returns a JSON dump of that user's
  Identity/Episodic/Emotional nodes, for debugging/demo purposes.
- Structured extraction (step 4) must use a typed schema (Pydantic models:
  `IdentityItem`, `EpisodicItem`, `EmotionalItem`) passed as LangChain tool
  schemas to the LLM — not regex/free-text parsing.
- Include at least 5 unit tests covering: categorization splitting a mixed
  message into multiple types, identity upsert overwriting a prior value,
  episodic append-only behavior, emotional trend aggregation query, and one
  end-to-end pipeline test with a mocked LLM.
- `.env.example` listing `ANTHROPIC_API_KEY`, `NEO4J_URI`, `NEO4J_USER`,
  `NEO4J_PASSWORD`, `MODEL_NAME`.
- `docker-compose.yml` brings up Neo4j, the official `mcp-neo4j-cypher`
  server, and the FastAPI app with one command. Document exact run steps
  (including a separate `npm install && npm run dev`/`build` step for the
  React frontend) in the README.
- README must document: setup, how memory categorization decisions are
  made, the graph schema, how the official Neo4j MCP server is configured
  and invoked, and any assumptions/decisions you made where this spec was
  ambiguous.

## ACCEPTANCE CRITERIA

- `docker-compose up` starts Neo4j and the API without manual steps beyond
  filling in `.env`.
- Sending two related chat turns (e.g., "I'm a nurse, night shifts are
  exhausting me" then later "how's work going?") demonstrably retrieves and
  uses stored identity/emotional context in the second reply — verify this
  in a test or documented manual walkthrough.
- `GET /memory/{user_id}` shows correctly categorized nodes after a few
  turns of conversation.
- All tests pass.

Build this now, fully, without pausing to ask me questions — make and
document sensible defaults for anything unspecified.
