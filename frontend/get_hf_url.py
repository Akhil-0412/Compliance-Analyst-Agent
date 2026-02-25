import requests
res = requests.get('https://huggingface.co/api/spaces/Akhil-008/Agentic_Compliance_Analyst')
data = res.json()
print("Subdomain:", data.get("subdomain"))
print("Host:", data.get("host"))
