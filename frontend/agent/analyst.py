# agent/analyst.py

from agent.redactor import redact_pii
from agent.router import route_query
from agent.prompts import ANALYST_PROMPT

from agent.llm_client import (
    run_llm_with_failover,
    groq_call,
    openrouter_call
)

from reasoning.extractor import enforce_reasoning
from reasoning.schema import AnalysisOutput

from validation import validate_all
from validation.temporal import validate_temporal_consistency
from agent.time_context import extract_event_date

from governance.engine import classify
from agent.response_builder import build_response


def analyze(user_query: str):
    # Step 1: Privacy boundary
    redacted_query, pii_map = redact_pii(user_query)

    # Step 2: Deterministic routing
    model = route_query(redacted_query)

    # Step 3: LLM invocation (structured + failover)
    llm_response = run_llm_with_failover(
        primary_fn=groq_call,
        fallback_fn=openrouter_call,
        model=model,
        prompt=ANALYST_PROMPT,
        input=redacted_query,
        response_model=AnalysisOutput
    )

    # Step 4: Enforce reasoning structure
    analysis = enforce_reasoning(llm_response)

    # Step 5: Check for Preconditions (New Workflow)
    if analysis.needs_clarification:
        decision = "CLARIFICATION_REQUIRED"
    else:
        # Step 6: Validation (hard guardrails)
        try:
            validate_all(analysis, redacted_query)
        except Exception as e:
            print(f"WARNING: Validation error (non-fatal): {e}")

        # Step 7: Governance decision
        decision = classify(analysis, query=redacted_query)

        # Step 8: Temporal consistency
        event_date = extract_event_date(redacted_query)
        temporal_decision = validate_temporal_consistency(
            analysis.reasoning_map,
            event_date
        )

        # Only downgrade to REVIEW_REQUIRED if not already BLOCKED
        if decision != "BLOCKED":
            if temporal_decision == "REVIEW_REQUIRED" and analysis.risk_level != "Low":
                decision = "REVIEW_REQUIRED"

    # Step 8: Final response
    return build_response(analysis, decision)
