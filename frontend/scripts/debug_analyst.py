import sys
import os
from dotenv import load_dotenv

load_dotenv()

# Add project root to sys.path
sys.path.append(os.getcwd())

try:
    from agent.analyst import analyze
    print("✅ Imported analyze")
except Exception as e:
    print(f"❌ Failed to import analyze: {e}")
    sys.exit(1)

# Test case with mixed data: Email (Art 6) vs Health Data (Art 9) vs Transfer (Art 46)
tests = [
    {
        "name": "Test 1: Transfer to Germany (No Art 46)",
        "query": "We store EU customer data on encrypted servers located in Germany.",
        "expected_art": "NONE"
    },
    {
        "name": "Test 2: Criminal Background Checks (Art 10)",
        "query": "We process criminal background check data for hiring decisions.",
        "expected_art": "10"
    },
    {
        "name": "Test 3: Employee Payroll (Art 6 only, No CCPA)",
        "query": "We process employee salary and tax information for employment contracts.",
        "expected_art": "6"
    }
]

for test in tests:
    print(f"\n🔬 Running {test['name']}: '{test['query']}'")
    try:
        result = analyze(test['query'])
        analysis = result['analysis']
        
        found_articles = []
        for node in analysis.reasoning_map:
            print(f"FOUND_ARTICLE: {node.regulation} {node.article}")
            found_articles.append(node.article)
            
        if not found_articles:
            print("NO ARTICLES FOUND")
            
        print(f"  Risk Level: {analysis.risk_level}")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
