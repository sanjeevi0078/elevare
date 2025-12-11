"""
Create a demo idea for user_id=5 (sanjeevi) to demonstrate the system working
"""
import redis
import json
from datetime import datetime

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Get current timestamp as float (matching API format)
import time
timestamp = time.time()

# Create a realistic demo idea for user 5
demo_idea = {
    "id": 999,
    "user_id": "5",  # Your user ID!
    "created_at": timestamp,  # Float timestamp
    "overall_confidence_score": 0.84,  # Required field
    "refined_idea": {
        "idea_title": "AI-Powered EdTech Platform for Personalized Learning",
        "problem_statement": "Traditional education systems fail to adapt to individual learning styles, pace, and needs, resulting in student disengagement and poor learning outcomes.",
        "solution": "An AI-driven educational platform that analyzes student behavior, learning patterns, and performance to create personalized learning paths with adaptive content delivery, real-time feedback, and gamification elements.",
        "target_market": "K-12 schools, tutoring centers, and homeschooling families in India and Southeast Asia",
        "revenue_model": "Freemium SaaS with tiered subscriptions for schools ($50-200/month), B2C monthly plans for families ($10-30/month), and enterprise licenses for school districts",
        "key_features": [
            "AI-powered learning path generation",
            "Real-time student performance analytics",
            "Adaptive content difficulty adjustment",
            "Interactive video lessons with quizzes",
            "Gamification with rewards and leaderboards",
            "Parent and teacher dashboards",
            "Multi-language support (English, Tamil, Hindi)",
            "Offline mode for low-connectivity areas"
        ],
        "competitive_advantage": "Hyper-personalization using advanced ML models, affordable pricing for emerging markets, offline-first architecture for rural areas, and curriculum alignment with regional education boards",
        "required_skills": ["Full-stack development", "Machine Learning", "EdTech domain knowledge", "UI/UX design", "Data science"],
        "timeline": "18-24 months to MVP and initial market traction",
        "estimated_budget": "$75,000 - $150,000"
    },
    "market_profile": {  # Required field - add dummy market data
        "target_audience": "K-12 schools, tutoring centers, homeschooling families",
        "market_size": "$300B global EdTech market",
        "growth_rate": "16.3% CAGR",
        "competitors": ["Khan Academy", "Byju's", "Coursera"],
        "competitive_edge": "Affordable personalization for emerging markets"
    },
    "dimensional_analysis": {
        "innovation_index": 0.82,
        "feasibility_score": 0.78,
        "market_viability": 0.85,
        "scalability": 0.88,
        "problem_score": 0.91,
        "solution_fit": 0.79,
        "overall_confidence": 0.84,
        "domain": "EdTech",
        "complexity_level": "Medium-High",
        "time_to_market_months": 18
    },
    "recommended_team": {
        "roles": [
            {"role": "Technical Co-founder / CTO", "skills": ["Python", "React", "Machine Learning", "Cloud Architecture"]},
            {"role": "Product Manager / Education Specialist", "skills": ["EdTech domain", "Curriculum design", "User research"]},
            {"role": "Full-stack Developer", "skills": ["Node.js", "React Native", "MongoDB", "API development"]},
            {"role": "ML Engineer", "skills": ["TensorFlow", "NLP", "Recommendation systems", "Data pipelines"]}
        ],
        "recommended_size": 4
    },
    "funding_requirements": {
        "seed_amount": "$100,000",
        "use_of_funds": {
            "Product Development": "45%",
            "Team Salaries": "35%",
            "Marketing & Customer Acquisition": "10%",
            "Infrastructure & Tools": "5%",
            "Legal & Compliance": "5%"
        },
        "milestones": [
            "MVP launch in 6 months",
            "100 paying customers in 12 months",
            "Break-even in 24 months"
        ]
    }
}

# Save to Redis
r.set(f"ideas:{demo_idea['id']}", json.dumps(demo_idea))

print("✅ Demo idea created successfully!")
print(f"📊 Idea ID: {demo_idea['id']}")
print(f"👤 User ID: {demo_idea['user_id']}")
print(f"💡 Title: {demo_idea['refined_idea']['idea_title']}")
print(f"🎯 Domain: {demo_idea['dimensional_analysis']['domain']}")
print(f"⭐ Confidence: {demo_idea['dimensional_analysis']['overall_confidence']}")
print("\n🔗 Now visit http://localhost:8000/user.html to see it on your dashboard!")
