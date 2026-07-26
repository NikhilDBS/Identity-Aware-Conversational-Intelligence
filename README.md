# Identity-Aware Conversational Intelligence (IACI)

A conversational agent that maintains three structured memory types about users in a **Neo4j graph** and uses them for context-aware, personalized conversations.

## Memory Types

| Type | What | Example |
|---|---|---|
| **Identity** | Durable facts about who the user *is* | "User is a backend engineer", "User prefers concise answers" |
| **Episodic** | Specific events with a *when* and *what happened* | "User had a job interview on July 20" |
| **Emotional** | Affective states tied to a trigger | "User feels anxious about job interviews" |

## Tech Stack

- **Backend**: FastAPI + LangGraph + LiteLLM (Mistral Medium 3)
- **Memory DB**: Neo4j (local, no Docker)
- **Memory Access**: Neo4j MCP server via `langchain-mcp-adapters`
- **Frontend**: React + Vite

---

## Setup

### 1. Neo4j

Install [Neo4j Desktop](https://neo4j.com/download/) or Community Server.

1. Start your Neo4j instance
2. Open Neo4j Browser at `http://localhost:7474`
3. Change the default password from `neo4j` to something of your choice
4. Note your password for the next step

### 2. Backend

```bash
cd backend

# Copy and fill in environment variables
cp .env.example .env
# Edit .env: set NEO4J_PASSWORD and MISTRAL_API_KEY

# Create virtual environment and install dependencies
python -m venv venv
.\venv\Scripts\activate        # Windows
# source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt

# Install the Neo4j MCP server
pip install neo4j-mcp-server

# Initialise the Neo4j schema (run once)
python scripts/init_schema.py

# Start the backend
uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`  
API docs at `http://localhost:8000/docs`

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`

---

## Pipeline Architecture

```
User message
     │
     ▼
assess_context         ← CoT LLM: needs retrieval? (structured JSON)
     │
     ├─ YES ──► retrieve_memory    ← Cypher templates → MCP read tool
     │
     ▼
extract_and_classify   ← CoT LLM: extract memories by type (structured JSON)
     │
     ├─ memories found ──► write_memory  ← Cypher templates → MCP write tool
     │
     ▼
generate_response      ← natural language, uses retrieved + new memories
```

Every node logs its decisions into a `trace` list returned with each API response and shown in the debug panel.

---

## API

```
POST /api/chat
  Body: { user_id, conversation_id, message }
  Returns: { response, conversation_id, trace }

GET /api/memory/{user_id}
  Returns: all memories stored for this user (debug)

GET /health
  Returns: status, model, neo4j uri, available MCP tools
```

---

## Graph Schema

```
(:User)-[:HAS_IDENTITY]->(:IdentityMemory)
(:User)-[:EXPERIENCED]->(:EpisodicMemory)
(:User)-[:FELT]->(:EmotionalMemory)
(:EpisodicMemory)-[:EVOKED]->(:EmotionalMemory)
(:Message)-[:PRODUCED]->(:IdentityMemory|:EpisodicMemory|:EmotionalMemory)
```

Every memory node is linked back to the `Message` that produced it for full provenance tracking.
