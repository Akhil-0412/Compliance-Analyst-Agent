"""
Agent State — The central TypedDict passed between all LangGraph nodes.
"""
from typing import TypedDict, Optional, Annotated
import operator


class AgentState(TypedDict):
    """Immutable state object flowing through the LangGraph pipeline."""

    # --- Conversation ---
    messages: Annotated[list[dict], operator.add]  # Full LLM conversation history
    user_query: str                                 # Original user input
    domain: str                                     # "GDPR" | "FDA" | "CCPA"

    # --- Retrieval ---
    retrieved_context: str                          # RAG text from FAISS / tools

    # --- Generation ---
    analysis: Optional[dict]                        # Serialized ComplianceResponse
    validation_errors: list[str]                    # Errors from _validate_response
    retry_count: int                                # Max 3 retries before fallback

    # --- Routing ---
    route: str                                      # "analysis" | "general" | "blocked"
    tool_calls: list[dict]                          # Pending tool call requests

    # --- Output ---
    final_response: Optional[dict]                  # The output returned to the API caller

    # --- Memory ---
    thread_id: str                                  # For SQLite checkpointer (Phase 3)

    # --- Clarification ---
    clarification_options: Optional[list]            # Ranked follow-up options for ambiguous queries
    user_selections: Optional[list]                  # User's selected clarification answers
