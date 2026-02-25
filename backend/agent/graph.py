"""
LangGraph Graph — Compiles the StateGraph with conditional edges.
This is the compiled agent that replaces ComplianceAgent._analyze_logic().
"""
from langgraph.graph import StateGraph, END

from agent.state import AgentState
from agent.nodes import (
    node_guardrail,
    node_chat,
    node_retrieve,
    node_clarify,
    node_llm,
    node_validator,
    node_semantic_override,
    node_governance,
    node_fallback,
    node_tool_executor,
    route_after_guardrail,
    route_after_clarify,
    route_after_llm,
    route_after_validation,
)


def build_graph() -> StateGraph:
    """Constructs the compliance agent graph."""

    graph = StateGraph(AgentState)

    # --- Register Nodes ---
    graph.add_node("guardrail", node_guardrail)
    graph.add_node("chat", node_chat)
    graph.add_node("retrieve", node_retrieve)
    graph.add_node("clarify", node_clarify)
    graph.add_node("llm", node_llm)
    graph.add_node("validator", node_validator)
    graph.add_node("semantic_override", node_semantic_override)
    graph.add_node("governance", node_governance)
    graph.add_node("fallback", node_fallback)
    graph.add_node("tool_executor", node_tool_executor)

    # --- Entry Point ---
    graph.set_entry_point("guardrail")

    # --- Conditional Edges ---
    # After guardrail: blocked → END, general → chat, analysis → retrieve
    graph.add_conditional_edges(
        "guardrail",
        route_after_guardrail,
        {
            "end": END,
            "chat": "chat",
            "retrieve": "retrieve",
        },
    )

    # Chat → END
    graph.add_edge("chat", END)

    # Retrieve → Clarify
    graph.add_edge("retrieve", "clarify")

    # After Clarify: clear → llm, depends → END (send options to user)
    graph.add_conditional_edges(
        "clarify",
        route_after_clarify,
        {
            "end": END,
            "llm": "llm",
        },
    )

    # After LLM: blocked → END, tool_call → tool_executor, answer → validator
    graph.add_conditional_edges(
        "llm",
        route_after_llm,
        {
            "end": END,
            "tool_executor": "tool_executor",
            "validator": "validator",
        },
    )

    # Tool Executor → back to LLM (ReAct cycle)
    graph.add_edge("tool_executor", "llm")

    # After Validator: pass → semantic_override, retry → llm, fallback → fallback
    graph.add_conditional_edges(
        "validator",
        route_after_validation,
        {
            "semantic_override": "semantic_override",
            "llm": "llm",
            "fallback": "fallback",
        },
    )

    # Semantic Override → Governance
    graph.add_edge("semantic_override", "governance")

    # Terminal nodes
    graph.add_edge("governance", END)
    graph.add_edge("fallback", END)

    return graph


def compile_graph(checkpointer=None):
    """Compiles the graph, optionally with a checkpointer for multi-turn memory."""
    graph = build_graph()

    if checkpointer:
        return graph.compile(checkpointer=checkpointer)
    return graph.compile()


# --- Default compiled graph with SQLite checkpointer for multi-turn memory ---
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import sqlite3

_DB_PATH = "checkpoints.db"

# We must use AsyncSqliteSaver for .astream() support.
# Since from_conn_string is an async context manager, we instantiate it directly 
# but we have to manage the connection. For global scope, we can use the 
# AsyncSqliteSaver with a local connection inside the graph if needed, but 
# we can just use the sync SqliteSaver for invoke() and AsyncSqliteSaver for astream().
from langgraph.checkpoint.sqlite import SqliteSaver
_conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
_checkpointer = SqliteSaver(_conn)
compiled_graph = compile_graph(checkpointer=_checkpointer)


def run_graph(user_query: str, domain: str = "GDPR", thread_id: str = "default") -> dict:
    """
    Public entry point: runs the compliance analysis graph.
    Uses thread_id for multi-turn conversation memory via SQLite checkpointer.
    """
    initial_state: AgentState = {
        "messages": [],
        "user_query": user_query,
        "domain": domain,
        "retrieved_context": "",
        "analysis": None,
        "validation_errors": [],
        "retry_count": 0,
        "route": "",
        "tool_calls": [],
        "final_response": None,
        "thread_id": thread_id,
        "clarification_options": None,
        "user_selections": None,
    }

    config = {"configurable": {"thread_id": thread_id}}
    result = compiled_graph.invoke(initial_state, config=config)
    return result.get("final_response", {"type": "error", "message": "No response generated."})


# --- Langfuse Observability ---
import os

def _get_langfuse_handler():
    """Returns a Langfuse CallbackHandler if keys are configured, else None."""
    secret = os.environ.get("LANGFUSE_SECRET_KEY")
    public = os.environ.get("LANGFUSE_PUBLIC_KEY")
    host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")

    if secret and public:
        try:
            from langfuse.callback import CallbackHandler
            return CallbackHandler(secret_key=secret, public_key=public, host=host)
        except Exception as e:
            print(f"[Langfuse] Init failed: {e}")
    return None


# --- Human-readable node labels for SSE ---
NODE_LABELS = {
    "guardrail": "Running intent safety check...",
    "chat": "Generating conversational response...",
    "retrieve": "Searching internal regulations...",
    "clarify": "Checking if clarification is needed...",
    "llm": "Generating compliance analysis...",
    "validator": "Validating LLM citations...",
    "semantic_override": "Applying regulatory overrides...",
    "governance": "Running governance decision gate...",
    "tool_executor": "Executing regulation lookup tool...",
    "fallback": "Analysis failed, returning fallback...",
}


async def stream_graph(user_query: str, domain: str = "GDPR", thread_id: str = "default", user_selections: list = None):
    """
    Async generator that streams node transitions as SSE events.
    Simultaneously pipes the execution trace to Langfuse.
    Yields: JSON string per node transition + final analysis.
    """
    import json as _json
    import traceback

    initial_state: AgentState = {
        "messages": [],
        "user_query": user_query,
        "domain": domain,
        "retrieved_context": "",
        "analysis": None,
        "validation_errors": [],
        "retry_count": 0,
        "route": "",
        "tool_calls": [],
        "final_response": None,
        "thread_id": thread_id,
        "clarification_options": None,
        "user_selections": user_selections,
    }

    config = {"configurable": {"thread_id": thread_id}}

    # Attach Langfuse if configured
    handler = _get_langfuse_handler()
    if handler:
        config["callbacks"] = [handler]

    last_state = {}
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    try:
        async with AsyncSqliteSaver.from_conn_string("checkpoints.db") as async_checkpointer:
            streaming_graph = compile_graph(checkpointer=async_checkpointer)

            async for output in streaming_graph.astream(initial_state, config=config):
                for node_name, state_update in output.items():
                    label = NODE_LABELS.get(node_name, f"Processing {node_name}...")
                    last_state.update(state_update)

                    # Stream the node transition event
                    yield _json.dumps({
                        "event": "node",
                        "node": node_name,
                        "label": label,
                        "retry_count": last_state.get("retry_count", 0),
                    })

            # Stream the final result — INSIDE the context manager
            final = last_state.get("final_response")
            if final:
                yield _json.dumps({"event": "result", "data": final})
            else:
                yield _json.dumps({"event": "result", "data": {"type": "error", "message": "No response generated."}})

    except Exception as e:
        tb = traceback.format_exc()
        print(f"[stream_graph] ERROR: {e}\n{tb}")
        yield _json.dumps({"event": "error", "data": {"type": "error", "message": str(e)}})

    yield "[DONE]"

