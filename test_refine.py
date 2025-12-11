import requests
import json

url = "http://localhost:8000/refine-idea"
payload = {
    "raw_idea_text": """
IDEA DESCRIPTION:
VoiceBridge is a real-time AI audio layer that helps people with speech impediments, severe social anxiety, or non-native language barriers communicate confidently in high-stakes environments.

PROBLEM STATEMENT:
Many people—especially those with anxiety, speech difficulty, or language barriers—struggle to communicate confidently. Their voice may shake, be unclear, or they might stutter. This prevents them from acing interviews, presentations, or phone calls, even though their ideas are brilliant.

SOLUTION:
An AI that converts speech-to-text AND text-to-speech in real-time, sitting between the user's microphone and their communication platform (Zoom, Teams). It smooths out stutters, removes filler words, and outputs a confident version of the user's own voice in under 200ms latency.

TARGET USER:
Neurodivergent professionals (ADHD/Autism), individuals with speech impediments, non-native English speakers in corporate jobs, and customer support agents who need accent standardization.

INDUSTRY/DOMAIN:
SaaS

RESOURCES NEEDED:
Technical Cofounder, Funding, Market Research
"""
}

try:
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Response JSON:")
        result = response.json()
        # Pretty print just the concept card
        if "concept_card" in result:
            print("\n=== CONCEPT CARD ===")
            print(json.dumps(result["concept_card"], indent=2))
    else:
        print("Response Text:")
        print(response.text)
except Exception as e:
    print(f"Error: {e}")

