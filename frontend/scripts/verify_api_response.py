import requests
import json
import socket
import time
import subprocess
import sys
import os

# Configuration
API_URL = "http://localhost:8002"
ENDPOINT = "/analyze"
TEST_QUERY = "We store user passwords in plain text on a public S3 bucket."

def wait_for_server(port, timeout=10):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection(("localhost", port), timeout=1):
                return True
        except (OSError, ConnectionRefusedError):
            time.sleep(1)
    return False

def verify_api():
    print(f"🚀 Starting verification for {API_URL}{ENDPOINT}...")
    
    payload = {"query": TEST_QUERY}
    
    try:
        response = requests.post(f"{API_URL}{ENDPOINT}", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API Request Successful")
            print(json.dumps(data, indent=2))
            
            # Validate structure
            if "analysis" in data and "decision" in data:
                print("✅ Response structure valid")
                
                analysis = data["analysis"]
                if "risk_level" in analysis and "reasoning_map" in analysis:
                     print("✅ Analysis schema validation proper")
                     return True
                else:
                     print("❌ Analysis schema missing fields")
            else:
                print("❌ Response missing root fields")
                
        else:
            print(f"❌ API Request Failed: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API server. Is it running?")
    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}")

    return False

if __name__ == "__main__":
    # Optional: Logic to start server if not running could go here, 
    # but for now we assume the user/agent starts it or we check connectivity.
    if not wait_for_server(8002, timeout=1):
        print("⚠️ Server not detected on port 8002. Please start the server first.")
        print("Run: uvicorn api.main:app --reload --port 8002")
        sys.exit(1)
        
    success = verify_api()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
