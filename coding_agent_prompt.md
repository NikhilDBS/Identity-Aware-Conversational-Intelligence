# Project Brief: Identity-Aware Conversational Intelligence (IACI)

> Give this entire document to your coding agent as the system/project prompt. It defines the architecture, memory model, pipeline, and build order. This is a **local-only research prototype** — do not add production concerns (auth, scaling, CI/CD, containerized Neo4j) unless explicitly asked.

## 1. What we're building

A conversational agent that maintains three distinct, structured memory types about the user in a Neo4j graph, and uses them to hold context-aware, personalized conversations. Every user turn is analyzed to decide (a) whether past memory needs to be retrieved to understand it, and (b) whether it contains new information worth storing, and if so, which memory category it belongs to.

### The three memory types

| Type | Definition | Change frequency | Example |
|---|---|---|---|
| **Identity memory** | Durable facts about who the user *is* — traits, preferences, values, roles, relationships, long-term goals | Low | "User is a backend engineer", "User prefers concise answers", "User's sister is named Meera" |
| **Episodic memory** | A specific event/experience with a *when* and a *what happened* | Medium (accumulates) | "User had a job interview on July 20", "User traveled to Goa last weekend" |
| **Emotional memory** | An affective state tied to a trigger — an event, topic, or person | Medium, decays/reinforces over time | "User feels anxious about job interviews", "User expressed joy discussing their dog" |

A single user message can produce zero, one, or multiple memory writes across categories (e.g., "I bombed my interview today and I'm scared I'll never get hired" → one episodic memory + one emotional memory, possibly reinforcing an existing identity trait like "career-anxious").

## 2. Tech stack (fixed — do not substitute)

- **Backend**: FastAPI (Python)
- **Orchestration**: LangChain + **LangGraph** (see §4 for why LangGraph, not plain sequential chains)
- **LLM access**: **LiteLLM** — provider-agnostic, so model choice is a config value (`LITELLM_MODEL=anthropic/claude-sonnet-4-6`, `openai/gpt-4o-mini`, `ollama/llama3`, etc.), not hardcoded
- **Database**: Neo4j, run **locally** (Neo4j Desktop or `neo4j` Community Server binary) — **no Docker**. Backend connects via `bolt://localhost:7687`.
- **Memory access layer**: **Official Neo4j MCP server** (`github.com/neo4j/mcp`, installed via `pip install neo4j-mcp-server`, launched via `python -m neo4j_mcp_server`)
- **Frontend**: React (Vite is fine), simple chat UI

### About the official Neo4j MCP server

- Exposes tools for schema introspection and Cypher execution (read and write).
- Read/write is controlled by the `NEO4J_READ_ONLY` env var — it **must be set to `false`** for this project, since the agent needs to write memories, not just read them.
- It's designed to be launched as a stdio subprocess by an MCP client. Since our LangGraph agent (not Claude Desktop/Cursor) needs to call it, use **`langchain-mcp-adapters`** to spin up the server as a subprocess and expose its tools as native LangChain/LangGraph tools. Do not try to hit it over HTTP unless you explicitly configure the server for HTTP transport — default is stdio.
- Example MCP server env config:
  ```
  NEO4J_URI=bolt://localhost:7687
  NEO4J_USERNAME=neo4j
  NEO4J_PASSWORD=<local password>
  NEO4J_DATABASE=neo4j
  NEO4J_READ_ONLY=false
  ```

## 3. Neo4j graph schema

Design the graph like this (adjust field names as needed, but keep the shape):

**Nodes**
- `(:User {id, name, created_at})`
- `(:Conversation {id, started_at})`
- `(:Message {id, role, content, timestamp})`
- `(:IdentityMemory {id, category, content, confidence, created_at, updated_at})`
  - `category` ∈ {trait, preference, value, role, relationship, goal}
- `(:EpisodicMemory {id, content, event_type, occurred_at, location, participants})`
- `(:EmotionalMemory {id, content, emotion_label, intensity, valence, trigger, occurred_at})`
  - `valence` ∈ {positive, negative, neutral, mixed}, `intensity` is 0.0–1.0

**Relationships**
- `(:User)-[:HAS_IDENTITY]->(:IdentityMemory)`
- `(:User)-[:EXPERIENCED]->(:EpisodicMemory)`
- `(:User)-[:FELT]->(:EmotionalMemory)`
- `(:EpisodicMemory)-[:EVOKED]->(:EmotionalMemory)` — an event that caused a feeling
- `(:EmotionalMemory)-[:REINFORCES]->(:IdentityMemory)` — recurring feelings shaping a trait
- `(:Conversation)-[:CONTAINS]->(:Message)`
- `(:Message)-[:PRODUCED]->(:IdentityMemory|:EpisodicMemory|:EmotionalMemory)` — provenance, always link new memories back to the message that generated them

**Setup**: write a one-time `scripts/init_schema.py` (or `.cypher` file) that creates uniqueness constraints on each node's `id` and a couple of indexes (e.g. on `EpisodicMemory.occurred_at`, `EmotionalMemory.trigger`). Run this manually once against the local Neo4j instance — this does not go through the MCP server.

## 4. Pipeline architecture (LangGraph, not plain LangChain chains)

Plain sequential LangChain `LLMChain`s don't model conditional branches well ("retrieve only if needed", "write 0-N memories of different types"). Use **LangGraph** — it's part of the LangChain ecosystem and is built exactly for stateful, conditional, multi-step agent flows. Model the pipeline as a graph with a shared state object.

### Graph state (shared across nodes)
```python
class PipelineState(TypedDict):
    user_id: str
    conversation_id: str
    user_message: str
    needs_retrieval: bool
    retrieval_queries: list[str]
    retrieved_context: list[dict]
    extracted_memories: list[dict]   # each: {type, category/emotion_label, content, metadata}
    final_response: str
    trace: list[dict]                # log every decision for debugging/research visibility
```

### Nodes

1. **`assess_context`** — CoT prompt to the LLM (via LiteLLM): given the message + recent conversation turns, decide `needs_retrieval` (bool) and, if true, produce natural-language retrieval intents (e.g. "check if user has mentioned job interviews before"). Force structured JSON output (use LangChain's `with_structured_output` with a Pydantic model — do this at every LLM step in this pipeline, not just this one).

2. **`retrieve_memory`** *(conditional edge — only runs if `needs_retrieval`)* — translate retrieval intents into Cypher via the LLM or a small templated query library (prefer templates for reliability; free-form Cypher generation is a nice stretch goal but riskier for a research prototype), call the MCP `read-cypher` tool, store results in `retrieved_context`.

3. **`extract_and_classify`** — CoT prompt: given the user message + `retrieved_context`, extract candidate memory items and classify each into identity / episodic / emotional with full structured metadata (confidence, valence/intensity for emotional, occurred_at for episodic, etc). It's fine and expected for this to return an empty list on many turns (small talk, clarifying questions).

4. **`write_memory`** *(conditional edge — only runs if `extracted_memories` is non-empty)* — for each item, generate a parameterized Cypher `MERGE`/`CREATE` write (again, prefer a small set of Cypher templates keyed by category over fully free-form generation), call the MCP write tool, and link the new node back to the current `Message` node via `PRODUCED`.

5. **`generate_response`** — compose the final reply using: user message, `retrieved_context`, and the memories just written (so the response can naturally acknowledge new information). Not forced JSON — this is the natural-language output.

Wire nodes 1→(2)→3→(4)→5, with conditional edges around 2 and 4 based on the boolean/list-emptiness checks. Log every node's decision into `trace` — this is a research project, so visibility into *why* the agent retrieved or stored something matters more than raw latency.

## 5. FastAPI backend structure

```
backend/
  app/
    main.py                      # FastAPI app, CORS for local React dev server
    api/routes/chat.py           # POST /chat {user_id, conversation_id, message} -> {response, trace}
    core/config.py               # env vars: LITELLM_MODEL, NEO4J_*, MCP server path
    graph/
      state.py                   # PipelineState TypedDict
      nodes/
        assess_context.py
        retrieve_memory.py
        extract_and_classify.py
        write_memory.py
        generate_response.py
      graph_builder.py           # builds & compiles the LangGraph graph
    mcp/
      client.py                  # launches neo4j-mcp-server via langchain-mcp-adapters, exposes tools
      cypher_templates.py        # parameterized read/write Cypher per memory category
    models/
      schemas.py                 # Pydantic models: IdentityItem, EpisodicItem, EmotionalItem, ChatRequest/Response
  scripts/init_schema.py
  requirements.txt
  .env.example
```

Keep the API surface minimal: one `/chat` endpoint is enough for a research prototype. Optionally add a `/memory/{user_id}` debug endpoint that dumps the current graph for that user (handy for the frontend debug panel below).

## 6. React frontend

Minimal chat UI: message list + input box, calling `POST /chat`. Since this is a research tool, it's worth adding a **collapsible debug panel** next to the chat that shows the `trace` returned per turn (what was retrieved, what was classified and stored, into which category) — this is far more valuable for this project than visual polish. Don't build user auth, routing, or a design system; a single page is fine.

## 7. Build order (do this in stages, don't build everything at once)

1. Set up local Neo4j (Desktop or Community Server), confirm bolt connection, run `init_schema.py` to create constraints.
2. Install and manually verify the Neo4j MCP server works standalone: `NEO4J_READ_ONLY=false python -m neo4j_mcp_server`, confirm you can run a read and a write Cypher query through it.
3. Scaffold FastAPI app with a stub `/chat` endpoint that echoes input — confirm the server runs and CORS works with a bare React fetch call.
4. Wire up `langchain-mcp-adapters` to the MCP server subprocess; confirm LangChain tools are generated from it and a manual tool call round-trips to Neo4j.
5. Build the LangGraph pipeline node-by-node in the order in §4, testing each node in isolation with a fake `PipelineState` before wiring the full graph.
6. Wire the compiled graph into the `/chat` endpoint.
7. Build the React chat UI + debug trace panel.
8. Only after the above works end-to-end: iterate on prompt quality for classification accuracy, add the `REINFORCES`/`EVOKED` relationship logic, add memory-decay or confidence-update logic if desired.

## 8. Guardrails for the coding agent

- This is a **local research prototype** — favor readability and inspectability over performance, security hardening, or deployment concerns.
- Do not Dockerize Neo4j. Do not add authentication. Do not add production logging/observability stacks — plain structured logs + the in-pipeline `trace` are enough.
- Every LLM call that needs to make a decision (retrieval, classification) must use structured/forced JSON output via Pydantic schemas — do not parse free-text LLM output with regex.
- Prefer a small library of parameterized Cypher templates over having the LLM freely generate Cypher, especially for writes — this is much easier to debug and keeps the graph schema consistent.
- Keep the LLM model swappable at all times through LiteLLM — never hardcode a provider SDK call.
- Always link new memory nodes back to the `Message` that produced them (`PRODUCED` relationship) — this provenance is what will make the debug/research work meaningful later.
