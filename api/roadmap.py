"""
AI-Powered Personalized Roadmap Generation
Generates custom startup roadmaps based on refined idea profiles
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
import redis

from config import settings
from logger import logger
from exceptions import RedisError, IdeaNotFoundError

router = APIRouter(tags=["roadmap"])

# Lazy Groq client initialization
groq_client: Optional[Any] = None
try:
    from groq import Groq
    api_key = os.getenv("GROQ_API_KEY")
    if api_key:
        groq_client = Groq(api_key=api_key)
except Exception as e:
    logger.exception("Failed to initialize Groq client for roadmap generation")

def get_redis() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL)


class RoadmapPhase(BaseModel):
    """Single phase in the roadmap"""
    phase_number: int
    title: str
    subtitle: str
    timeline: str  # e.g., "Month 1-2", "Q1 2024"
    description: str
    key_activities: List[str]
    deliverables: List[str]
    success_metrics: List[str]
    estimated_cost: Optional[str] = None
    risk_level: str = "Medium"  # Low, Medium, High


class PersonalizedRoadmap(BaseModel):
    """Complete personalized roadmap for a startup idea"""
    idea_id: int
    idea_title: str
    core_domain: str
    total_duration_months: int
    phases: List[RoadmapPhase]
    critical_path: List[str]
    funding_requirements: Dict[str, str]
    team_requirements: Dict[str, int]
    generated_at: float


# Domain-specific roadmap templates
ROADMAP_SYSTEM_PROMPT = """You are a **Senior Startup Strategist** with 20+ years helping founders from idea to IPO across FinTech, HealthTech, EdTech, SaaS, E-commerce, and ClimateTech.

Your mission: Create a **hyper-personalized, actionable roadmap** for the founder's specific startup idea.

ANALYZE the refined idea profile and generate a SINGLE JSON object with EXACTLY this structure:

{
  "total_duration_months": <integer 6-24 based on complexity>,
  "phases": [
    {
      "phase_number": 1,
      "title": "string - Phase name (e.g., 'MVP Development', 'Market Validation')",
      "subtitle": "string - One-line summary of this phase's goal",
      "timeline": "string - Time range (e.g., 'Month 1-3', 'Q1 2025')",
      "description": "string - Detailed explanation of what happens in this phase (200-400 chars)",
      "key_activities": ["array of 4-6 specific actionable tasks unique to this idea"],
      "deliverables": ["array of 3-5 tangible outputs from this phase"],
      "success_metrics": ["array of 3-4 measurable KPIs for this phase"],
      "estimated_cost": "string - Budget range (e.g., '$5K-$10K', '$50K-$100K', 'Bootstrapped')",
      "risk_level": "Low|Medium|High"
    }
    // ... typically 4-6 phases total
  ],
  "critical_path": ["array of 3-5 non-negotiable milestones that MUST happen in order"],
  "funding_requirements": {
    "seed": "string - Seed funding needed and rationale",
    "series_a": "string - Series A projections if applicable",
    "bootstrap_viable": "Yes|No - Can this be bootstrapped?"
  },
  "team_requirements": {
    "founders": <integer 1-3>,
    "early_hires": <integer 0-10>,
    "contractors": <integer 0-5>
  }
}

CRITICAL INSTRUCTIONS:
1. **Domain-Specific Logic**:
   - FinTech: Emphasize compliance, security audits, banking partnerships, regulatory milestones
   - HealthTech: HIPAA compliance, clinical validation, FDA approval if hardware/biotech
   - EdTech: Curriculum design, pilot programs with schools, accreditation
   - SaaS: Beta testing, user onboarding, churn optimization, scalability testing
   - E-commerce: Supplier partnerships, logistics, payment gateway integration
   - ClimateTech: Environmental impact metrics, certification, sustainability audits

2. **Feasibility-Based Pacing**:
   - Feasibility 1.0-2.0 (deep tech): 18-24 months, heavy R&D phases
   - Feasibility 2.5-3.5 (standard SaaS): 12-18 months, iterative development
   - Feasibility 4.0-5.0 (simple app): 6-12 months, rapid MVP

3. **Market Viability Impact**:
   - High viability (>3.5): Aggressive timelines, focus on growth/scaling phases
   - Low viability (<2.0): Extra validation phase, pivot checkpoints, customer discovery

4. **Personalization Depth**:
   - Use ACTUAL idea title in phase descriptions (not generic "your app")
   - Reference SPECIFIC target users (not "users")
   - Mention ACTUAL solution concept details in activities

5. **Realism Over Hype**:
   - Include realistic costs (not "TBD")
   - Acknowledge risks honestly
   - Phase timelines should overlap slightly (real projects aren't waterfall)

6. **Output Format**:
   - ONLY output the JSON object
   - NO markdown code fences
   - NO commentary outside JSON

EXAMPLES:

**Bad Activity**: "Build the app"
**Good Activity**: "Develop iOS prototype with core calorie tracking feature using HealthKit integration"

**Bad Deliverable**: "Working product"
**Good Deliverable**: "Beta version of expense tracker with Plaid API integration supporting 3 major banks"

**Bad Success Metric**: "Users are happy"
**Good Success Metric**: "30 beta users complete 5+ expense entries per week with <5% churn"

NOW PROCESS THE IDEA AND RETURN THE PERSONALIZED ROADMAP JSON:
"""


def _generate_fallback_roadmap(idea_profile: Dict[str, Any]) -> PersonalizedRoadmap:
    """Generate a template-based roadmap when AI is unavailable (rate limits, etc.)"""
    refined = idea_profile.get("refined_idea", {})
    market = idea_profile.get("market_profile", {})
    
    idea_title = refined.get("idea_title", "Your Startup")
    domain = refined.get("core_domain", "SaaS")
    target_user = refined.get("target_user", "target users")
    feasibility = refined.get("initial_feasibility_score", 3.0)
    
    # Determine timeline based on feasibility
    if feasibility <= 2.0:
        total_months = 18
        timeline_suffix = "deep tech"
    elif feasibility <= 3.5:
        total_months = 12
        timeline_suffix = "standard"
    else:
        total_months = 9
        timeline_suffix = "rapid MVP"
    
    # Domain-specific customizations
    domain_specifics = {
        "Fintech": {
            "compliance": "Regulatory compliance and security audits",
            "phase1_extra": "Banking partner identification",
            "phase3_extra": "PCI-DSS compliance certification"
        },
        "HealthTech": {
            "compliance": "HIPAA compliance and data security",
            "phase1_extra": "Healthcare stakeholder interviews",
            "phase3_extra": "Clinical validation pilot"
        },
        "EdTech": {
            "compliance": "Educational standards alignment",
            "phase1_extra": "Curriculum design consultation",
            "phase3_extra": "School pilot program"
        },
        "SaaS": {
            "compliance": "SOC2 Type I preparation",
            "phase1_extra": "User journey mapping",
            "phase3_extra": "Scalability load testing"
        },
        "E-commerce": {
            "compliance": "Payment gateway compliance",
            "phase1_extra": "Supplier network research",
            "phase3_extra": "Logistics partner integration"
        },
        "ClimateTech": {
            "compliance": "Environmental impact certification",
            "phase1_extra": "Sustainability metrics definition",
            "phase3_extra": "Carbon footprint audit"
        }
    }
    
    specifics = domain_specifics.get(domain, domain_specifics["SaaS"])
    
    phases = [
        RoadmapPhase(
            phase_number=1,
            title="Discovery & Validation",
            subtitle=f"Validate {idea_title} concept with real {target_user}",
            timeline="Month 1-2",
            description=f"Deep dive into the problem space. Interview potential users, analyze competitors, and refine the value proposition for {idea_title}.",
            key_activities=[
                f"Conduct 20+ user interviews with {target_user}",
                "Competitive analysis and market sizing",
                specifics["phase1_extra"],
                "Define MVP feature set based on feedback",
                "Create detailed user personas and journey maps"
            ],
            deliverables=[
                "User research synthesis document",
                "Competitive landscape analysis",
                "MVP specification document",
                "Go/No-Go decision framework"
            ],
            success_metrics=[
                "20+ validated user interviews completed",
                "3+ key pain points identified and prioritized",
                "MVP scope defined with <10 core features"
            ],
            estimated_cost="$2K-$5K",
            risk_level="Low"
        ),
        RoadmapPhase(
            phase_number=2,
            title="MVP Development",
            subtitle=f"Build core {idea_title} functionality",
            timeline="Month 2-4",
            description=f"Develop the minimum viable product focusing on the core value proposition. Prioritize speed to market while maintaining quality.",
            key_activities=[
                "Set up development environment and CI/CD pipeline",
                "Implement core features (80/20 rule)",
                "Design responsive UI/UX",
                "Integrate essential third-party services",
                "Implement basic analytics tracking"
            ],
            deliverables=[
                "Working MVP with core features",
                "Technical documentation",
                "Basic admin dashboard",
                "User onboarding flow"
            ],
            success_metrics=[
                "MVP feature completion rate >90%",
                "Core user flow completion time <5 minutes",
                "Zero critical bugs in main user journey"
            ],
            estimated_cost="$10K-$25K",
            risk_level="Medium"
        ),
        RoadmapPhase(
            phase_number=3,
            title="Beta Launch & Iteration",
            subtitle="Test with early adopters and iterate",
            timeline="Month 4-6",
            description=f"Launch {idea_title} to a controlled group of beta users. Collect feedback, measure engagement, and rapidly iterate.",
            key_activities=[
                "Recruit 50-100 beta users",
                "Implement feedback collection system",
                specifics["phase3_extra"],
                "Weekly iteration sprints based on feedback",
                "A/B test key features and flows"
            ],
            deliverables=[
                "Beta version with 2-3 iteration cycles",
                "User feedback database",
                "Feature prioritization backlog",
                "Beta user testimonials"
            ],
            success_metrics=[
                "50+ active beta users",
                "Weekly retention rate >40%",
                "NPS score >30",
                "Feature adoption rate >60%"
            ],
            estimated_cost="$5K-$15K",
            risk_level="Medium"
        ),
        RoadmapPhase(
            phase_number=4,
            title="Public Launch",
            subtitle=f"Launch {idea_title} to the market",
            timeline=f"Month 6-{min(total_months-3, 8)}",
            description="Execute go-to-market strategy. Focus on user acquisition, conversion optimization, and establishing market presence.",
            key_activities=[
                "Finalize pricing strategy",
                "Launch marketing campaigns",
                "Implement customer support system",
                "Optimize conversion funnels",
                "Build partnerships and integrations"
            ],
            deliverables=[
                "Production-ready platform",
                "Marketing website and materials",
                "Customer success playbook",
                "Partnership pipeline"
            ],
            success_metrics=[
                "500+ registered users in first month",
                "Customer acquisition cost <$50",
                "Conversion rate >3%",
                "Support ticket resolution <24 hours"
            ],
            estimated_cost="$15K-$40K",
            risk_level="High"
        ),
        RoadmapPhase(
            phase_number=5,
            title="Growth & Scale",
            subtitle="Scale operations and revenue",
            timeline=f"Month {min(total_months-3, 8)}-{total_months}",
            description=f"Focus on sustainable growth, team expansion, and preparing {idea_title} for the next funding round or profitability.",
            key_activities=[
                "Implement growth loops and referral program",
                "Expand to new market segments",
                "Hire key team members",
                "Establish scalable processes",
                specifics["compliance"]
            ],
            deliverables=[
                "Scalable infrastructure",
                "Growth playbook",
                "Team expansion plan",
                "Investor-ready metrics dashboard"
            ],
            success_metrics=[
                "Month-over-month growth >15%",
                "Customer lifetime value >3x CAC",
                "Team size 3-5 people",
                "Monthly recurring revenue target achieved"
            ],
            estimated_cost="$30K-$100K",
            risk_level="High"
        )
    ]
    
    return PersonalizedRoadmap(
        idea_id=idea_profile.get("id", 0),
        idea_title=idea_title,
        core_domain=domain,
        total_duration_months=total_months,
        phases=phases,
        critical_path=[
            "Complete user validation before building",
            "Launch MVP within 4 months",
            "Achieve product-market fit signal (NPS >30)",
            "Hit growth targets before scaling team"
        ],
        funding_requirements={
            "seed": "$50K-$150K for MVP development and initial launch",
            "series_a": "$500K-$2M for scaling (if product-market fit achieved)",
            "bootstrap_viable": "Yes" if feasibility >= 3.5 else "Partial"
        },
        team_requirements={
            "founders": 1 if feasibility >= 4 else 2,
            "early_hires": 2 if feasibility >= 3 else 4,
            "contractors": 3
        },
        generated_at=datetime.now().timestamp()
    )


def _generate_roadmap_with_groq(idea_profile: Dict[str, Any]) -> PersonalizedRoadmap:
    """Generate personalized roadmap using Groq AI, with fallback on failure"""
    global groq_client
    
    if not groq_client:
        logger.warning("Groq client not available, using fallback roadmap generator")
        return _generate_fallback_roadmap(idea_profile)
    
    refined = idea_profile.get("refined_idea", {})
    market = idea_profile.get("market_profile", {})
    
    # Build context for AI
    context = f"""
IDEA PROFILE:
Title: {refined.get('idea_title', 'Unnamed Idea')}
Problem: {refined.get('problem_statement', 'N/A')}
Solution: {refined.get('solution_concept', 'N/A')}
Target User: {refined.get('target_user', 'N/A')}
Domain: {refined.get('core_domain', 'Other')}
Location: {refined.get('suggested_location', 'Global')}
Feasibility Score: {refined.get('initial_feasibility_score', 3.0)}/5.0
Market Viability: {market.get('market_viability_score', 0.0)}/5.0
Competitors: {market.get('raw_competitor_count', 'Unknown')}
Overall Confidence: {idea_profile.get('overall_confidence_score', 0.0)}/5.0
"""
    
    try:
        response = groq_client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            messages=[
                {"role": "system", "content": ROADMAP_SYSTEM_PROMPT},
                {"role": "user", "content": context}
            ],
            temperature=0.3,  # Lower temp for more consistent structure
            max_tokens=2000,
        )
        
        content = response.choices[0].message.content
        
        # Extract JSON from response
        content = content.strip()
        if content.startswith("```"):
            import re
            content = re.sub(r"```(?:json)?", "", content, flags=re.IGNORECASE)
        
        # Parse JSON
        roadmap_data = json.loads(content)
        
        # Build PersonalizedRoadmap object
        return PersonalizedRoadmap(
            idea_id=idea_profile.get("id", 0),
            idea_title=refined.get("idea_title", "Unnamed Idea"),
            core_domain=refined.get("core_domain", "Other"),
            total_duration_months=roadmap_data.get("total_duration_months", 12),
            phases=[RoadmapPhase(**phase) for phase in roadmap_data.get("phases", [])],
            critical_path=roadmap_data.get("critical_path", []),
            funding_requirements=roadmap_data.get("funding_requirements", {}),
            team_requirements=roadmap_data.get("team_requirements", {}),
            generated_at=datetime.now().timestamp()
        )
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Groq roadmap response: {e}. Using fallback.")
        return _generate_fallback_roadmap(idea_profile)
    except Exception as e:
        logger.warning(f"Groq roadmap generation failed: {e}. Using fallback template.")
        return _generate_fallback_roadmap(idea_profile)


@router.post("/generate", response_model=PersonalizedRoadmap)
def generate_roadmap(idea_id: int, r: redis.Redis = Depends(get_redis)) -> PersonalizedRoadmap:
    """
    Generate a personalized roadmap for a specific idea
    
    Args:
        idea_id: ID of the refined idea
        
    Returns:
        PersonalizedRoadmap with custom phases, timelines, and milestones
    """
    try:
        # Fetch idea from Redis
        idea_raw = r.get(f"ideas:{idea_id}")
        if not idea_raw:
            raise IdeaNotFoundError(idea_id=idea_id)
        
        idea_profile = json.loads(idea_raw)
        
        # Check if roadmap already exists in cache
        cached_roadmap = r.get(f"roadmap:{idea_id}")
        if cached_roadmap:
            logger.info(f"Returning cached roadmap for idea {idea_id}")
            return PersonalizedRoadmap(**json.loads(cached_roadmap))
        
        # Generate new roadmap
        logger.info(f"Generating AI roadmap for idea {idea_id}")
        roadmap = _generate_roadmap_with_groq(idea_profile)
        
        # Cache for 7 days
        r.setex(
            f"roadmap:{idea_id}",
            7 * 24 * 60 * 60,
            roadmap.model_dump_json()
        )
        
        logger.info(f"✅ Generated {len(roadmap.phases)}-phase roadmap for '{roadmap.idea_title}'")
        return roadmap
        
    except IdeaNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to generate roadmap: {e}", exc_info=True)
        raise RedisError(message="Failed to generate roadmap", original_error=e)


@router.get("/idea/{idea_id}", response_model=PersonalizedRoadmap)
def get_roadmap(idea_id: int, r: redis.Redis = Depends(get_redis)) -> PersonalizedRoadmap:
    """Get existing roadmap or generate if not exists"""
    try:
        # Try cache first
        cached = r.get(f"roadmap:{idea_id}")
        if cached:
            return PersonalizedRoadmap(**json.loads(cached))
        
        # Generate if not exists
        return generate_roadmap(idea_id, r)
        
    except Exception as e:
        logger.error(f"Failed to retrieve roadmap: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}", response_model=List[PersonalizedRoadmap])
def list_user_roadmaps(user_id: str, r: redis.Redis = Depends(get_redis)) -> List[PersonalizedRoadmap]:
    """List all roadmaps for a user's ideas"""
    try:
        # Get all user's ideas
        idea_ids = [int(x) for x in r.lrange("ideas:list", 0, -1)]
        roadmaps = []
        
        for idea_id in idea_ids:
            idea_raw = r.get(f"ideas:{idea_id}")
            if not idea_raw:
                continue
                
            idea_data = json.loads(idea_raw)
            if idea_data.get("user_id") != user_id:
                continue
            
            # Get or generate roadmap
            try:
                roadmap = get_roadmap(idea_id, r)
                roadmaps.append(roadmap)
            except:
                continue
        
        return roadmaps
        
    except Exception as e:
        logger.error(f"Failed to list user roadmaps: {e}")
        return []
