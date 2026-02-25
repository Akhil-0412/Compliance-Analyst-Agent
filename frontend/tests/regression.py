import json
from agent.analyst import analyze
from tests.utils import risk_at_least
from dotenv import load_dotenv

load_dotenv()

def load_cases(path):
    with open(path, "r") as f:
        return json.load(f)

def run_case(case):
    result = analyze(case["input"])

    analysis = result["analysis"]
    decision = result["decision"]

    articles = {node.article for node in analysis.reasoning_map}

    expected = case["expected"]

    for a in expected["articles_present"]:
        # Allow substring match (e.g. "33" matches "Article 33(1)")
        found = any(a in actual for actual in articles)
        assert found, f"Missing article {a} in {articles}"

    for a in expected["articles_absent"]:
        assert a not in articles, f"Unexpected article {a}"

    assert risk_at_least(
        analysis.risk_level,
        expected["min_risk"]
    ), "Risk too low"

    assert decision == expected["decision"], "Wrong governance decision"

def test_golden_gdpr():
    cases = load_cases("tests/golden/gdpr_cases.json")
    for case in cases:
        run_case(case)
