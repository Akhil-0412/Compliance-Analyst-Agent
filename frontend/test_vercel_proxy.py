import requests
import json

URL = "https://agentic-compliance-agent-v2.vercel.app/api/analyze"

payload = {
    "query": "We lost patient data",
    "domain": "GDPR",
    "model_tier": "Tier 1"
}

print(f"Sending POST request to {URL}...")
try:
    response = requests.post(URL, json=payload, timeout=30)
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {response.headers}")
    try:
        data = response.json()
        print("Response JSON:")
        print(json.dumps(data, indent=2))
    except json.JSONDecodeError:
        print("Response Text:")
        print(response.text)
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
