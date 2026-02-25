import json
import sys
import traceback
from dotenv import load_dotenv

# Load env vars immediately
load_dotenv()

from agent.analyst import analyze

# ansi colors
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

def load_cases(path):
    with open(path, "r") as f:
        return json.load(f)

def run_case_verification(case):
    print(f"Running Case {case['id']}...", end=" ")
    try:
        result = analyze(case["input"])
        
        # Analyze structure
        if isinstance(result, str):
            # Handle BLOCKED or Error strings
            if case["expected"]["decision"] == "BLOCKED":
                if "BLOCKED" in result:
                     print(f"{GREEN}PASSED{RESET}")
                     return
                else:
                     raise AssertionError(f"Expected BLOCKED, got string: {result}")
            else:
                raise AssertionError(f"Unexpected string response: {result}")

        analysis = result["analysis"] # AnalysisOutput object
        decision = result["decision"]
        
        # Serialize to string for searching articles
        # We search in summary AND reasoning map logic
        analysis_text = analysis.summary + " " + str(analysis.model_dump())

        # Articles check (String match in analysis text)
        for a in case["expected"]["articles_present"]:
            if a not in analysis_text:
                 raise AssertionError(f"Missing article {a} in response")

        for a in case["expected"]["articles_absent"]:
             if a in analysis_text:
                 raise AssertionError(f"Unexpected article {a} in response")

        # Risk Check
        expected_risk = case["expected"]["min_risk"]
        # Logic: High > Medium > Low
        risk_map = {"Low": 1, "Medium": 2, "High": 3}
        # Access risk_level from the Pydantic object
        actual_risk_val = risk_map.get(getattr(analysis, "risk_level", "Low"), 0)
        expected_risk_val = risk_map.get(expected_risk, 0)
        
        if actual_risk_val < expected_risk_val:
             raise AssertionError(f"Risk {getattr(analysis, 'risk_level', 'None')} < {expected_risk}")
        
        # Decision Check
        if decision != case["expected"]["decision"]:
             raise AssertionError(f"Expected {case['expected']['decision']}, got {decision}")
        
        print(f"{GREEN}PASSED{RESET}")
        return True

    except AssertionError as e:
        print(f"{RED}FAILED{RESET}")
        print(f"  Reason: {e}")
        return False
    except Exception as e:
        print(f"{RED}ERROR{RESET}")
        print(f"  Exception: {str(e)}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    cases_path = "tests/golden/edge_cases.json"
    print(f"Loading cases from {cases_path}...")
    
    try:
        cases = load_cases(cases_path)
    except FileNotFoundError:
        print(f"{RED}Critical Error: Could not find golden dataset at {cases_path}{RESET}")
        sys.exit(1)

    failed_count = 0
    for case in cases:
        success = run_case_verification(case)
        if not success:
            failed_count += 1
            
    print("-" * 40)
    if failed_count == 0:
        print(f"{GREEN}All cases PASSED.{RESET}")
        sys.exit(0)
    else:
        print(f"{RED}{failed_count} cases FAILED.{RESET}")
        sys.exit(1)
