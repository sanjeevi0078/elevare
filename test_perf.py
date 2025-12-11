import time
import requests
import json

url = "http://localhost:8000/matching/users"
payload = {
    "name": "Performance Test User",
    "email": f"perf_test_{int(time.time())}@example.com",
    "skills": ["python", "fastapi", "performance", "testing"],
    "interest": "High Performance Computing",
    "personality": "Analyst"
}

print(f"Sending request to {url}...")
start_time = time.time()
try:
    response = requests.post(url, json=payload)
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"Status Code: {response.status_code}")
    print(f"Duration: {duration:.4f} seconds")
    if response.status_code == 200:
        print("Response:", response.json())
    else:
        print("Error:", response.text)
except Exception as e:
    print(f"Request failed: {e}")
