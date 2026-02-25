import requests
import json

URL = "https://akhil-008-agentic-compliance-analyst-aa53283.hf.space/api/chat"

payload = {
    "query": "We lost patient data",
    "domain": "GDPR",
    "model_tier": "Tier 1"
}

print(f"Sending POST request to {URL}...")
try:
    response = requests.post(URL, json=payload, timeout=30)
    print(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        print("Error Detail:", data.get("detail", data))
    except Exception:
        print(response.text)
        print(response.text)
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
