#!/usr/bin/env python3
"""
Demo Data Script for Elevare Platform
Creates sample user profiles for demonstration purposes
"""

import requests
import json

API_BASE = "http://localhost:8000"

# Sample users with diverse profiles
DEMO_USERS = [
    {
        "name": "Alice Chen",
        "email": "alice.chen@example.com",
        "location": "San Francisco",
        "interest": "Fintech",
        "personality": "Analytical",
        "commitment_level": 0.9,
        "skills": ["Python", "Machine Learning", "Data Science", "Finance"]
    },
    {
        "name": "Bob Martinez",
        "email": "bob.martinez@example.com",
        "location": "Austin",
        "interest": "HealthTech",
        "personality": "Creative",
        "commitment_level": 0.8,
        "skills": ["React", "Node.js", "UI/UX Design", "Healthcare"]
    },
    {
        "name": "Carol Johnson",
        "email": "carol.johnson@example.com",
        "location": "New York",
        "interest": "EdTech",
        "personality": "Organized",
        "commitment_level": 0.85,
        "skills": ["Product Management", "Marketing", "Education", "Strategy"]
    },
    {
        "name": "David Kim",
        "email": "david.kim@example.com",
        "location": "Seattle",
        "interest": "SaaS",
        "personality": "Technical",
        "commitment_level": 0.95,
        "skills": ["Go", "Kubernetes", "DevOps", "Cloud Architecture"]
    },
    {
        "name": "Emma Wilson",
        "email": "emma.wilson@example.com",
        "location": "London",
        "interest": "E-commerce",
        "personality": "Entrepreneurial",
        "commitment_level": 0.9,
        "skills": ["Sales", "Business Development", "E-commerce", "Growth Hacking"]
    },
    {
        "name": "Frank Zhang",
        "email": "frank.zhang@example.com",
        "location": "Bangalore",
        "interest": "ClimateTech",
        "personality": "Visionary",
        "commitment_level": 0.88,
        "skills": ["IoT", "Sustainability", "Hardware", "Environmental Science"]
    },
    {
        "name": "Grace Lee",
        "email": "grace.lee@example.com",
        "location": "San Francisco",
        "interest": "Fintech",
        "personality": "Detail-oriented",
        "commitment_level": 0.92,
        "skills": ["Blockchain", "Smart Contracts", "Solidity", "Finance"]
    },
    {
        "name": "Henry Brown",
        "email": "henry.brown@example.com",
        "location": "Boston",
        "interest": "HealthTech",
        "personality": "Collaborative",
        "commitment_level": 0.87,
        "skills": ["Mobile Development", "Swift", "Healthcare", "Telemedicine"]
    }
]

def create_users():
    """Create demo users via API"""
    print("🚀 Creating demo users for Elevare Platform...\n")
    
    created_users = []
    
    for user_data in DEMO_USERS:
        try:
            response = requests.post(
                f"{API_BASE}/matching/users",
                json=user_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                user = response.json()
                created_users.append(user)
                print(f"✅ Created user: {user['name']} (ID: {user['id']})")
            else:
                error = response.json()
                # Check if user already exists
                if "duplicate" in str(error).lower() or "unique" in str(error).lower():
                    print(f"⚠️  User {user_data['name']} already exists, skipping...")
                else:
                    print(f"❌ Failed to create {user_data['name']}: {error}")
        except Exception as e:
            print(f"❌ Error creating {user_data['name']}: {e}")
    
    print(f"\n✨ Successfully created {len(created_users)} users!")
    
    if created_users:
        print("\n📊 Sample User IDs for testing:")
        for user in created_users[:3]:
            print(f"   - {user['name']}: ID {user['id']}")
        
        print("\n💡 Try finding matches for these users in the frontend!")
        print(f"   Frontend: {API_BASE}")
        print(f"   API Docs: {API_BASE}/docs")

def test_idea_validation():
    """Test the idea validation endpoint"""
    print("\n\n🧪 Testing Idea Validation...\n")
    
    sample_idea = {
        "raw_idea_text": "A mobile app that helps freelancers track their time and generate invoices automatically. Target users are freelance designers and developers in urban areas."
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/refine-idea",
            json=sample_idea,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Idea validation successful!")
            print(f"   Title: {result['refined_idea']['idea_title']}")
            print(f"   Domain: {result['refined_idea']['core_domain']}")
            print(f"   Overall Score: {result['overall_confidence_score']}/5.0")
        else:
            print(f"❌ Idea validation failed: {response.json()}")
    except Exception as e:
        print(f"❌ Error testing idea validation: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("  Elevare Platform - Demo Data Setup")
    print("=" * 60)
    print()
    
    # Check if server is running
    try:
        response = requests.get(f"{API_BASE}/")
        print("✅ Server is running\n")
    except Exception as e:
        print(f"❌ Server is not running at {API_BASE}")
        print("   Please start the server first: ./start.sh")
        exit(1)
    
    # Create demo users
    create_users()
    
    # Test idea validation
    test_idea_validation()
    
    print("\n" + "=" * 60)
    print("  Demo data setup complete! 🎉")
    print("=" * 60)
