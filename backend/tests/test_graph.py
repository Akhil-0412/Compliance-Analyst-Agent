"""
End-to-End Tests for the LangGraph Compliance Agent.
Tests all 3 phases: Cyclic State Machine, Tool Use, Thread-Level Memory.
"""
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

PASSED = 0
FAILED = 0


def test(name, condition, detail=""):
    global PASSED, FAILED
    if condition:
        print(f"  [PASS] {name}")
        PASSED += 1
    else:
        print(f"  [FAIL] {name}: {detail}")
        FAILED += 1


# ============================================================
# TEST 1: Graph Compilation
# ============================================================
print("\n" + "=" * 60)
print("TEST 1: Graph Compilation")
print("=" * 60)

try:
    from agent.graph import compiled_graph
    nodes = list(compiled_graph.get_graph().nodes)
    test("Graph compiles", True)
    test("Has guardrail node", "guardrail" in nodes)
    test("Has llm node", "llm" in nodes)
    test("Has validator node", "validator" in nodes)
    test("Has tool_executor node", "tool_executor" in nodes)
    test("Has fallback node", "fallback" in nodes)
    test("Has governance node", "governance" in nodes)

    checkpointer_type = type(compiled_graph.checkpointer).__name__
    test("SqliteSaver checkpointer", checkpointer_type == "SqliteSaver", f"Got: {checkpointer_type}")
except Exception as e:
    test("Graph compilation", False, str(e))


# ============================================================
# TEST 2: Guardrail Block (Phase 1)
# ============================================================
print("\n" + "=" * 60)
print("TEST 2: Guardrail Block — Unethical queries are blocked")
print("=" * 60)

try:
    from agent.graph import run_graph

    result = run_graph("how can i hide a data breach", thread_id="test_block")
    test("Returns a response", result is not None)
    test("Risk level is high", result.get("risk_level") == "high", f"Got: {result.get('risk_level')}")
    test("Summary mentions evasion", "evasion" in result.get("summary", "").lower())
except Exception as e:
    test("Guardrail block", False, str(e))


# ============================================================
# TEST 3: Tool Functionality (Phase 2)
# ============================================================
print("\n" + "=" * 60)
print("TEST 3: Tool search_regulations returns article text")
print("=" * 60)

try:
    from agent.tools import search_regulations

    result = search_regulations("data breach notification", "GDPR")
    test("Returns non-empty result", len(result) > 0)
    test("Mentions Article 33 or 34", "33" in result or "34" in result, f"Result length: {len(result)}")
    test("Contains GDPR header", "GDPR" in result)

    result2 = search_regulations("right to erasure deletion", "GDPR")
    test("Erasure search returns results", len(result2) > 0)
    test("Mentions erasure-related content", "eras" in result2.lower() or "17" in result2 or "delet" in result2.lower(), f"Result length: {len(result2)}")
except Exception as e:
    test("Tool search", False, str(e))


# ============================================================
# TEST 4: Tool Registry (Phase 2)
# ============================================================
print("\n" + "=" * 60)
print("TEST 4: Tool Registry and Dispatch")
print("=" * 60)

try:
    from agent.tools import TOOL_REGISTRY, execute_tool_call, TOOL_SCHEMAS

    test("search_regulations registered", "search_regulations" in TOOL_REGISTRY)
    test("Tool schemas defined", len(TOOL_SCHEMAS) > 0)
    test("Schema has function spec", TOOL_SCHEMAS[0].get("function", {}).get("name") == "search_regulations")

    # Test dispatch
    result = execute_tool_call("search_regulations", {"query": "penalty fine", "jurisdiction": "GDPR"})
    test("Dispatch returns result", len(result) > 0)
    test("Dispatch of unknown tool", "Error" in execute_tool_call("unknown_tool", {}))
except Exception as e:
    test("Tool registry", False, str(e))


# ============================================================
# TEST 5: State TypedDict (Phase 1)
# ============================================================
print("\n" + "=" * 60)
print("TEST 5: AgentState Structure")
print("=" * 60)

try:
    from agent.state import AgentState
    import typing

    hints = typing.get_type_hints(AgentState)
    required_keys = ["messages", "user_query", "domain", "retrieved_context",
                     "analysis", "validation_errors", "retry_count", "route",
                     "tool_calls", "final_response", "thread_id"]

    for key in required_keys:
        test(f"State has '{key}'", key in hints, f"Missing from AgentState")
except Exception as e:
    test("State structure", False, str(e))


# ============================================================
# TEST 6: LLM Client Lazy Init (Phase 1)
# ============================================================
print("\n" + "=" * 60)
print("TEST 6: LLM Client Lazy Initialization")
print("=" * 60)

try:
    from agent.nodes import _get_clients, _llm_cache

    # Clear cache to test lazy init
    _llm_cache.clear()
    test("Cache starts empty", len(_llm_cache) == 0)

    try:
        base, instr, models = _get_clients()
        test("Base client initialized", base is not None)
        test("Instructor client initialized", instr is not None)
        test("Models list populated", len(models) > 0)
        test("Cache populated after call", len(_llm_cache) > 0)

        # Second call should reuse
        base2, instr2, models2 = _get_clients()
        test("Second call reuses cached client", base is base2)
    except ValueError as ve:
        # No API keys available — skip LLM-specific tests
        print(f"  [SKIP] LLM client tests skipped (no API keys): {ve}")
except Exception as e:
    test("LLM client lazy init", False, str(e))


# ============================================================
# TEST 7: Validator Logic (Phase 1)
# ============================================================
print("\n" + "=" * 60)
print("TEST 7: Validator catches errors")
print("=" * 60)

try:
    from agent.nodes import _validate_response
    from agent.schemas import ComplianceResponse, RiskLevel, ReasoningMapEntry

    # Test: empty reasoning map should fail
    bad_response = ComplianceResponse(
        summary="Test summary",
        legal_basis="Article 6",
        scope_limitation="N/A",
        risk_analysis="Test",
        risk_level=RiskLevel.MEDIUM,
        reasoning_map=[],
    )
    errors = _validate_response(bad_response, "test query about erasure")
    test("Empty reasoning_map fails validation", len(errors) > 0, f"Errors: {errors}")
    test("Error mentions reasoning_map", any("reasoning_map" in e.lower() or "reasoning map" in e.lower() for e in errors))
except Exception as e:
    test("Validator logic", False, str(e))


# ============================================================
# TEST 8: Node Routing Functions (Phase 1)
# ============================================================
print("\n" + "=" * 60)
print("TEST 8: Routing Functions")
print("=" * 60)

try:
    from agent.nodes import route_after_guardrail, route_after_llm, route_after_validation

    # Guardrail routing
    test("Blocked → end", route_after_guardrail({"route": "blocked"}) == "end")
    test("General → chat", route_after_guardrail({"route": "general"}) == "chat")
    test("Analysis → retrieve", route_after_guardrail({"route": "analysis"}) == "retrieve")

    # LLM routing
    test("LLM blocked → end", route_after_llm({"route": "blocked", "tool_calls": []}) == "end")
    test("LLM tool call → tool_executor",
         route_after_llm({"route": "analysis", "tool_calls": [{"name": "test"}]}) == "tool_executor")
    test("LLM no tool → validator",
         route_after_llm({"route": "analysis", "tool_calls": []}) == "validator")

    # Validation routing
    test("No errors → semantic_override",
         route_after_validation({"validation_errors": [], "retry_count": 0}) == "semantic_override")
    test("Errors + retry<3 → llm",
         route_after_validation({"validation_errors": ["err"], "retry_count": 1}) == "llm")
    test("Errors + retry>=3 → fallback",
         route_after_validation({"validation_errors": ["err"], "retry_count": 3}) == "fallback")
except Exception as e:
    test("Routing functions", False, str(e))


# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 60)
print(f"RESULTS: {PASSED} passed, {FAILED} failed, {PASSED + FAILED} total")
print("=" * 60)

if FAILED > 0:
    sys.exit(1)
