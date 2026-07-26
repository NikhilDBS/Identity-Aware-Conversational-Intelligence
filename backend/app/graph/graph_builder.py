"""
LangGraph graph builder — wires all 5 pipeline nodes with conditional edges.

Flow:
  assess_context
       │
       ├─ needs_retrieval=True  ──► retrieve_memory ─┐
       └─ needs_retrieval=False ────────────────────┘
                                                     ▼
                                           extract_and_classify
                                                     │
                                ├─ memories found ──► write_memory ─┐
                                └─ no memories ──────────────────┘
                                                                    ▼
                                                           generate_response
                                                                    │
                                                                   END
"""
from __future__ import annotations

from langgraph.graph import StateGraph, END, START

from app.graph.state import PipelineState
from app.graph.nodes.assess_context      import assess_context
from app.graph.nodes.retrieve_memory     import retrieve_memory
from app.graph.nodes.extract_and_classify import extract_and_classify
from app.graph.nodes.write_memory        import write_memory
from app.graph.nodes.generate_response   import generate_response


def _route_after_assess(state: PipelineState) -> str:
    return "retrieve_memory" if state.get("needs_retrieval") else "extract_and_classify"


def _route_after_extract(state: PipelineState) -> str:
    return "write_memory" if state.get("extracted_memories") else "generate_response"


def build_graph():
    """Build and compile the LangGraph pipeline. Call once at startup."""
    graph = StateGraph(PipelineState)

    # ── Register nodes ────────────────────────────────────────────────────────
    graph.add_node("assess_context",       assess_context)
    graph.add_node("retrieve_memory",      retrieve_memory)
    graph.add_node("extract_and_classify", extract_and_classify)
    graph.add_node("write_memory",         write_memory)
    graph.add_node("generate_response",    generate_response)

    # ── Entry point ───────────────────────────────────────────────────────────
    graph.add_edge(START, "assess_context")

    # ── Conditional edge: assess_context → [retrieve | extract] ──────────────
    graph.add_conditional_edges(
        "assess_context",
        _route_after_assess,
        {
            "retrieve_memory":      "retrieve_memory",
            "extract_and_classify": "extract_and_classify",
        },
    )

    # ── retrieve_memory always leads to extract_and_classify ──────────────────
    graph.add_edge("retrieve_memory", "extract_and_classify")

    # ── Conditional edge: extract_and_classify → [write | generate] ──────────
    graph.add_conditional_edges(
        "extract_and_classify",
        _route_after_extract,
        {
            "write_memory":      "write_memory",
            "generate_response": "generate_response",
        },
    )

    # ── write_memory always leads to generate_response ────────────────────────
    graph.add_edge("write_memory", "generate_response")

    # ── Terminal node ─────────────────────────────────────────────────────────
    graph.add_edge("generate_response", END)

    return graph.compile()


# Module-level compiled graph — imported by the FastAPI route
compiled_graph = build_graph()
