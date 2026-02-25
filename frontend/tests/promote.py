import json

def promote_to_golden(case, analysis, decision, path):
    golden_case = {
        "id": case["id"],
        "input": case["input"],
        "expected": {
            "articles_present": [n.article for n in analysis.reasoning_map],
            "articles_absent": [],
            "min_risk": analysis.risk_level,
            "decision": decision
        }
    }

    with open(path, "r+") as f:
        data = json.load(f)
        data.append(golden_case)
        f.seek(0)
        json.dump(data, f, indent=2)
