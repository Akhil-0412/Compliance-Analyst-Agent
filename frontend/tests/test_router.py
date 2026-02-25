import pytest
from agent.router import score_complexity, route_query

def test_critical_keywords():
    # "breach" should force max score
    text = "We had a data breach involving 500 users."
    score = score_complexity(text)
    assert score == 1.0
    assert route_query(text) == "gemini-1.5-pro"

def test_simple_definition():
    # Short definition query should be low score
    text = "What is the GDPR?"
    score = score_complexity(text)
    assert score < 0.25
    assert route_query(text) == "llama-3-8b"

def test_drafting_intent():
    # Drafting bumps score
    text = "Draft a privacy policy for my mobile app that uses camera data."
    score = score_complexity(text)
    # Length is short-ish, but Drafting (+0.2) + Regulation keywords should bump it
    assert score > 0.3
    assert route_query(text) in ["llama-3-70b", "gemini-1.5-pro"]

def test_complex_scenario():
    # Long text with multiple factors
    text = """
    If a user from California asks to delete their data, but we have a legal obligation 
    under tax law to keep records for 5 years, how do we handle this request under CCPA 
    and GDPR? We want to avoid any fines or penalties.
    """
    # "penalty" is a critical keyword -> 1.0
    score = score_complexity(text)
    assert score == 1.0
    assert route_query(text) == "gemini-1.5-pro"
