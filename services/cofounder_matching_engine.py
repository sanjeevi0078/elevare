"""
Cofounder Matching Engine
=========================

AI-Powered matching engine that uses LLM to analyze startup ideas and find
compatible cofounders based     except Exception as e:
        logger.error(f"AI matching error for {candidate_profile.get('name')}: {e}")
        candidate_name = candidate_profile.get('name', 'Unknown')
        skills = candidate_profile.get('skills', [])
        skills_preview = ', '.join(skills[:3]) if skills else 'various areas'
        
        return AIMatchResult(
            id=str(candidate_profile.get('id', 'unknown')),
            name=candidate_name,
            role_type="Potential Match",
            match_percentage=0,
            synergy_analysis="Analysis failed. Please try again.",
            missing_skills_filled=[],
            recommended_action="Review",
            intro_message=f"Hi {candidate_name}, I saw your profile and think we could collaborate. Your experience in {skills_preview} caught my attention. Let's connect!",
            location=candidate_profile.get('location'),
            bio=candidate_profile.get('bio'),
            skills=skills,
            interests=candidate_profile.get('interests', [])
        )y analysis, not just keyword matching.

Core Components:
1.  **AI Persona Analysis**: LLM generates ideal cofounder profile from idea
2.  **Smart Matching**: Grades candidates against idea-specific requirements
3.  **Explainable Results**: Provides WHY each match makes sense
4.  **Multi-Source Data**: Integrates GitHub, database profiles, and external APIs
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional

import httpx
from pydantic import BaseModel, Field
from config import settings, Environment
from groq import Groq

from sqlalchemy.orm import Session
from sqlalchemy import select
from models.user_models import User

# --- CONFIGURATION ---
logger = logging.getLogger(__name__)

# Initialize Groq Client for AI Matching
groq_client = None
groq_api_key = os.getenv("GROQ_API_KEY")
if groq_api_key:
    try:
        groq_client = Groq(api_key=groq_api_key)
        logger.info("✅ Groq AI matching engine initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Groq: {e}")
else:
    logger.warning("⚠️ GROQ_API_KEY not set. AI matching will use fallback mode.")

# Suppress noisy logs
logging.getLogger("urllib3").setLevel(logging.WARNING)


# --- DATA MODELS ---

class AIMatchResult(BaseModel):
    """AI-analyzed match result with explainability."""
    id: str  # Changed from user_id to match API response
    name: str
    role_type: str = "Co-founder"  # e.g., "Technical Architect", "Growth Lead"
    match_percentage: int
    synergy_analysis: str  # WHY this person fits THIS specific idea
    missing_skills_filled: List[str]  # Critical skills they bring
    recommended_action: str  # "Must Connect", "Strong Option", "Explore", "Pass"
    intro_message: str  # Personalized introduction message
    location: Optional[str] = None
    bio: Optional[str] = None
    skills: List[str] = []
    interests: List[str] = []
    
    # Contact & Social Media Fields
    username: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_username: Optional[str] = None
    avatar_url: Optional[str] = None
    profile_url: Optional[str] = None
    source: str = "local"  # 'local' or 'github'


def _local_heuristic_match(idea_text: str, candidate_profile: Dict) -> AIMatchResult:
    """Deterministic fallback matcher used when the LLM is unavailable or fails.

    Uses simple but explainable heuristics: skill overlap, interest/domain match,
    and bio keyword boosts. Returns a full AIMatchResult so the front-end gets
    meaningful scores and explanations instead of zeros or generic text.
    """
    # Extract idea requirements with existing parser
    req = parse_user_idea(idea_text)
    req_skills = set(s.lower() for s in req.required_skills)
    domain = req.domain.lower() if req.domain else ''

    candidate_skills = set(s.lower() for s in candidate_profile.get('skills', []))
    candidate_interests = set(i.lower() for i in candidate_profile.get('interests', []))
    bio = (candidate_profile.get('bio') or '').lower()

    # Skill overlap score (Jaccard-style)
    if req_skills and candidate_skills:
        inter = req_skills.intersection(candidate_skills)
        union = req_skills.union(candidate_skills)
        skill_score = len(inter) / max(1, len(union))
    else:
        skill_score = 0.0

    # Domain/interest boost
    domain_boost = 1.0 if (domain and (domain in candidate_interests or domain in bio)) else 0.0

    # Bio skill mentions give small boosts
    bio_boost = 0.0
    for s in req_skills:
        if s in bio:
            bio_boost += 0.05

    # Combine into a 0..1 score
    score = (skill_score * 0.75) + (domain_boost * 0.2) + bio_boost
    score = max(0.0, min(0.99, score))

    # Map to percentage
    pct = int(round(score * 100))

    # Build synergy analysis
    inter_skills = list(req_skills.intersection(candidate_skills))
    if inter_skills:
        synergy = f"Has {len(inter_skills)} key skill(s) relevant to the idea: {', '.join(inter_skills)}. Shows domain alignment in profile/bio."
    elif domain_boost > 0:
        synergy = f"Profile shows interest or experience in the {req.domain} domain; may bridge domain knowledge with product development."
    else:
        synergy = f"Limited explicit skill overlap; candidate may still contribute complementary strengths (experience, network, or execution)."

    # Missing skills they fill (top candidate skills)
    missing_filled = list(candidate_skills)[:4]

    # Recommended action thresholds
    if pct >= 80:
        action = 'Must Connect'
    elif pct >= 60:
        action = 'Strong Option'
    elif pct >= 40:
        action = 'Explore'
    else:
        action = 'Pass'

    candidate_name = candidate_profile.get('name', 'Candidate')
    skills_preview = ', '.join(list(candidate_skills)[:3]) if candidate_skills else 'various areas'

    intro = f"Hi {candidate_name.split()[0]}, I noticed your experience in {skills_preview}. I'm building a {req.domain} startup and think your background could add value — would you be open to a short chat?"

    return AIMatchResult(
        id=str(candidate_profile.get('id', 'unknown')),
        name=candidate_name,
        role_type="Potential Match",
        match_percentage=pct,
        synergy_analysis=synergy,
        missing_skills_filled=missing_filled,
        recommended_action=action,
        intro_message=intro,
        location=candidate_profile.get('location'),
        bio=candidate_profile.get('bio'),
        skills=candidate_profile.get('skills', []),
        interests=candidate_profile.get('interests', []),
        username=candidate_profile.get('username'),
        avatar_url=candidate_profile.get('avatar_url'),
        profile_url=candidate_profile.get('profile_url'),
        source=candidate_profile.get('source', 'local')
    )


def analyze_match_with_ai(idea_context: str, candidate_profile: Dict) -> AIMatchResult:
    """Primary entrypoint for matching a single candidate to an idea.

    Attempts an LLM analysis when available. If the LLM client is not
    configured or the LLM call/parse fails, falls back to a deterministic
    local heuristic so the UI gets useful, explainable results.
    """

    # If there's no Groq client, use the local heuristic (deterministic)
    if not groq_client:
        return _local_heuristic_match(idea_context, candidate_profile)

    # Build prompt with explicit JSON schema
    skills_str = ', '.join(candidate_profile.get('skills', [])) or 'Not specified'
    interests_str = ', '.join(candidate_profile.get('interests', [])) or 'Not specified'
    prompt = f"""You are an Expert Co-founder Matchmaker for startups.

**The Startup Idea:**
"{idea_context}"

**The Candidate Profile:**
Name: {candidate_profile.get('name', 'Candidate')}
Bio: {candidate_profile.get('bio', 'Not provided')}
Skills: {skills_str}
Interests: {interests_str}
Personality: {candidate_profile.get('personality', 'Not specified')}
Location: {candidate_profile.get('location', 'Not specified')}

**Your Task:**
Analyze if this candidate is a good co-founder fit for THIS SPECIFIC IDEA.
DO NOT do generic matching. Look for deep synergy.

Examples:
- Fintech idea → Look for Security, Compliance skills even if not explicitly mentioned
- Elderly app → Look for Accessibility, UX skills
- B2B SaaS → Look for Enterprise sales, API design

Return ONLY valid JSON with this EXACT structure (no other fields):
{{
    "role_type": "Suggested role title based on their strengths (e.g. 'CTO', 'CMO', 'Product Lead')",
    "match_percentage": <integer 0-100 based on idea-specific fit>,
    "synergy_analysis": "2-3 sentences explaining WHY they fit THIS specific idea (not generic skills)",
    "missing_skills_filled": ["List 2-4 specific skills/experience they bring that are critical for THIS idea"],
    "recommended_action": "One of: 'Must Connect' (80%+), 'Strong Option' (60-79%), 'Explore' (40-59%), 'Pass' (<40%)",
    "intro_message": "A personalized 2-3 sentence introduction message to send to this candidate (mention specific synergies with the idea)"
}}"""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a precise JSON-only matching engine. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        # Write raw response to debug log for later inspection (if available)
        try:
            raw = response.choices[0].message.content
            # append to debug file (best-effort)
            debug_path = os.path.join(os.path.dirname(__file__), '..', 'logs', 'cofounder_llm_responses.log')
            os.makedirs(os.path.dirname(debug_path), exist_ok=True)
            with open(debug_path, 'a') as fh:
                fh.write(json.dumps({'candidate': candidate_profile.get('id'), 'raw': raw}) + '\n')
        except Exception:
            # Non-fatal if logging fails
            pass

        # Parse JSON - if parsing fails, fall back to local heuristic
        try:
            result = json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Failed to parse LLM JSON for {candidate_profile.get('name')}: {e}")
            return _local_heuristic_match(idea_context, candidate_profile)

        candidate_name = candidate_profile.get('name', 'Unknown')

        return AIMatchResult(
            id=str(candidate_profile.get('id', 'unknown')),
            name=candidate_name,
            role_type=result.get('role_type', 'Co-founder'),
            match_percentage=max(0, min(100, int(result.get('match_percentage', 50)))),
            synergy_analysis=result.get('synergy_analysis', 'Analysis in progress...'),
            missing_skills_filled=result.get('missing_skills_filled', [])[:4],
            recommended_action=result.get('recommended_action', 'Explore'),
            intro_message=result.get('intro_message', f"Hi {candidate_name}, I think we could collaborate well on this project. Let's connect!"),
            location=candidate_profile.get('location'),
            bio=candidate_profile.get('bio'),
            skills=candidate_profile.get('skills', []),
            interests=candidate_profile.get('interests', []),
            username=candidate_profile.get('username'),
            avatar_url=candidate_profile.get('avatar_url'),
            profile_url=candidate_profile.get('profile_url'),
            source=candidate_profile.get('source', 'local')
        )

    except Exception as e:
        logger.error(f"AI matching error for {candidate_profile.get('name')}: {e}")
        # Fall back to local heuristic so UI remains useful
        return _local_heuristic_match(idea_context, candidate_profile)


def get_smart_matches(idea_text: str, db: Session, top_k: int = 10, exclude_user_id: int = None) -> List[AIMatchResult]:
    """
    AI-Powered Orchestrator:
    1. Takes the refined startup idea
    2. Fetches all user profiles from the database
    3. Runs deep LLM analysis on each candidate
    4. Sorts by AI-determined match percentage
    5. Returns top_k matches with explainability
    
    This replaces basic keyword matching with context-aware AI matching.
    """
    # Fetch all users from database (excluding current user if specified)
    query = select(User)
    if exclude_user_id:
        query = query.where(User.id != exclude_user_id)
    all_users = db.scalars(query).all()
    
    logger.info(f"🤖 Starting AI matching for {len(all_users)} candidates (excluding user {exclude_user_id})")
    results = []
    
    for user in all_users:
        try:
            # Convert User model to dict for analyze_match_with_ai
            candidate_dict = {
                'id': user.id,
                'name': user.name,
                'bio': getattr(user, 'personality', None) or getattr(user, 'bio', None),  # Use personality as bio
                'location': user.location,
                'personality': getattr(user, 'personality', None),
                'skills': [skill.name for skill in user.skills] if hasattr(user, 'skills') and user.skills else [],
                'interests': [i.strip() for i in user.interest.split(',')] if user.interest else [],
                # Social profile fields
                'username': getattr(user, 'github_username', None),
                'linkedin_url': getattr(user, 'linkedin_url', None),
                'email': user.email if user.email != 'not_set' else None,
                'avatar_url': getattr(user, 'avatar_url', None),
                'profile_url': getattr(user, 'profile_url', None),
                'source': getattr(user, 'source', 'local')
            }
            
            match = analyze_match_with_ai(idea_text, candidate_dict)
            results.append(match)
        except Exception as e:
            logger.error(f"Failed to analyze candidate {user.name}: {e}")
            continue
    
    # Sort by AI match percentage (descending)
    results.sort(key=lambda x: x.match_percentage, reverse=True)
    
    logger.info(f"✅ AI matching complete. Top match: {results[0].name if results else 'None'} ({results[0].match_percentage if results else 0}%)")
    
    return results[:top_k]


class FounderProfile(BaseModel):
    """Represents a potential co-founder profile from any source."""
    id: str = Field(..., description="Unique identifier (e.g., github_username)")
    name: Optional[str] = None
    source: str = Field(..., description="Origin of the data (e.g., 'github', 'wellfound')")
    profile_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_username: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    skills: List[str] = []
    interests: List[str] = []
    bio: Optional[str] = None
    location: Optional[str] = None
    activity_score: float = 0.0
    raw_data: Dict[str, Any] = {}


class IdeaRequirements(BaseModel):
    """Structured requirements extracted from a user's startup idea."""
    domain: str
    required_skills: List[str]
    tech_stack: List[str]
    project_stage: str = "early"
    text_for_embedding: str


class MatchResult(BaseModel):
    """A single ranked co-founder match."""
    profile: FounderProfile
    match_score: float = Field(..., description="Similarity score (0.0 to 1.0)")
    domain_fit: bool = False
    why_matched: str
    intro_message: str


# --- 1. DATA SOURCE CONNECTORS ---

def fetch_github_profiles(queries: List[str], max_per_query: int = 10) -> List[FounderProfile]:
    """
    Fetch developer profiles from GitHub based on search queries.
    """
    # Check feature flag
    if not settings.FEATURE_REAL_GITHUB_API:
        if settings.ENVIRONMENT == Environment.DEVELOPMENT:
            logger.info("Using mock GitHub profiles (FEATURE_REAL_GITHUB_API=False)")
            return [
                FounderProfile(id='mock_gh_user_1', name='Alex Tech', source='github', profile_url='https://github.com/alexthedev', skills=['python', 'fastapi', 'react'], interests=['ai', 'saas'], bio='Building the future of AI assistants.'),
                FounderProfile(id='mock_gh_user_2', name='Brenda Business', source='github', profile_url='https://github.com/brendabiz', skills=['marketing', 'strategy'], interests=['fintech', 'e-commerce'], bio='Growth marketer for startups.'),
            ]
        return []

    if not settings.GITHUB_API_TOKEN:
        logger.warning("GitHub API token not set, skipping GitHub search")
        return []

    profiles = []
    headers = {
        "Authorization": f"token {settings.GITHUB_API_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    with httpx.Client() as client:
        for query in queries:
            try:
                response = client.get(
                    f"{settings.GITHUB_API_URL}/search/users",
                    params={"q": query, "per_page": max_per_query},
                    headers=headers
                )
                if response.status_code == 200:
                    data = response.json()
                    for item in data.get("items", []):
                        # Fetch user details for bio/skills
                        try:
                            user_resp = client.get(item["url"], headers=headers)
                            if user_resp.status_code == 200:
                                user_data = user_resp.json()
                                profiles.append(FounderProfile(
                                    id=str(user_data["id"]),
                                    name=user_data.get("name") or user_data["login"],
                                    source="github",
                                    profile_url=user_data["html_url"],
                                    skills=[], # GitHub doesn't provide skills directly
                                    interests=[],
                                    bio=user_data.get("bio") or ""
                                ))
                        except Exception as e:
                            logger.error(f"Error fetching user details for {item['login']}: {e}")
            except Exception as e:
                logger.error(f"Error searching GitHub for {query}: {e}")
                
    return profiles


def fetch_founder_datasets() -> List[FounderProfile]:
    """
    Load founder profiles from local or remote JSON/CSV datasets.
    """
    # Only load dummy data in development
    if settings.ENVIRONMENT != Environment.DEVELOPMENT:
        return []

    dataset_path = os.path.join(os.path.dirname(__file__), 'founder_datasets', 'dummy_founders.json')
    if not os.path.exists(dataset_path):
        logger.warning(f"Dummy founder dataset not found at {dataset_path}")
        return []
    
    try:
        with open(dataset_path, 'r') as f:
            data = json.load(f)
        
        profiles = []
        for item in data:
            profiles.append(FounderProfile.model_validate(item))
            
        logger.info(f"Loaded {len(profiles)} profiles from local dataset.")
        return profiles
    except Exception as e:
        logger.error(f"Error loading founder dataset: {e}")
        return []
    return profiles


def merge_and_clean_profiles(profile_lists: List[List[FounderProfile]]) -> List[FounderProfile]:
    """
    Merge profiles from multiple sources and deduplicate.
    """
    merged: Dict[str, FounderProfile] = {}
    for profile_list in profile_lists:
        for profile in profile_list:
            if profile.id not in merged:
                merged[profile.id] = profile
    return list(merged.values())


# --- 2. USER IDEA PROCESSING ---

def parse_user_idea(idea_text: str) -> IdeaRequirements:
    """
    Parse the user's idea text to extract structured requirements.
    
    TODO: Replace with a more sophisticated NLP model (spaCy or local LLM).
    For now, uses simple keyword-based heuristics.
    """
    text_lower = idea_text.lower()
    
    # Heuristic skill extraction
    skills = []
    common_skills = ['python', 'javascript', 'react', 'node.js', 'fastapi', 'aws', 'docker', 'ai', 'ml', 'marketing', 'sales', 'ui/ux']
    for skill in common_skills:
        if skill in text_lower:
            skills.append(skill)
            
    # Heuristic domain extraction
    domain = "Other"
    domains = ["fintech", "healthtech", "edtech", "saas", "e-commerce"]
    for d in domains:
        if d in text_lower:
            domain = d.title()
            break
            
    return IdeaRequirements(
        domain=domain,
        required_skills=list(set(skills)),
        tech_stack=list(set(skills)), # Simplified for now
        text_for_embedding=f"Idea for a {domain} company. Required skills: {', '.join(skills)}. {idea_text}"
    )


# --- 3. MATCHING ENGINE ---

class CofounderMatchingEngine:
    """
    The core engine that embeds and ranks profiles against an idea.
    """
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model = None
        # self.model = SentenceTransformer(model_name) # TODO: Uncomment when library is installed
        logger.info("Matching engine initialized (model loading deferred).")

    def _embed_text(self, texts: List[str]) -> Optional[Any]:
        if not self.model:
            logger.warning("SentenceTransformer model not loaded. Cannot compute embeddings.")
            return None
        # return self.model.encode(texts, convert_to_tensor=True)
        pass

    def rank_profiles(self, requirements: IdeaRequirements, profiles: List[FounderProfile]) -> List[MatchResult]:
        """
        Rank profiles against idea requirements using semantic similarity or keyword matching.
        """
        results = []
        
        # Prepare requirements set
        req_skills = set(s.lower() for s in requirements.required_skills)
        domain = requirements.domain.lower()
        
        for profile in profiles:
            # Calculate score based on skills overlap and domain match
            profile_skills = set(s.lower() for s in profile.skills)
            profile_interests = set(i.lower() for i in profile.interests)
            
            # Jaccard similarity for skills
            if req_skills and profile_skills:
                intersection = req_skills.intersection(profile_skills)
                union = req_skills.union(profile_skills)
                skill_score = len(intersection) / len(union)
            else:
                skill_score = 0.0
                
            # Domain match bonus
            domain_score = 0.0
            if domain in profile_interests or any(domain in i for i in profile_interests):
                domain_score = 1.0
            
            # Weighted score (70% skills, 30% domain)
            final_score = (skill_score * 0.7) + (domain_score * 0.3)
            
            # Boost for bio keywords
            if profile.bio:
                bio_lower = profile.bio.lower()
                if domain in bio_lower:
                    final_score += 0.1
                for skill in req_skills:
                    if skill in bio_lower:
                        final_score += 0.05
            
            # Cap at 0.99
            final_score = min(0.99, final_score)
            
            if final_score < 0.1: continue # Minimum threshold
            
            why_matched = f"Matched on {len(req_skills.intersection(profile_skills))} skills and domain relevance."
            intro = f"Hi {profile.name.split()[0]}, I came across your profile and was impressed by your work in {profile.interests[0] if profile.interests else 'your domain'}. I'm building a startup in the {requirements.domain} space and thought your skills could be a great fit. Would you be open to a brief chat?"

            results.append(MatchResult(
                profile=profile,
                match_score=final_score,
                domain_fit=(domain_score > 0),
                why_matched=why_matched,
                intro_message=intro
            ))
            
        return sorted(results, key=lambda r: r.match_score, reverse=True)


# --- 4. API-FACING FUNCTION ---

def get_top_cofounders(idea_text: str, top_k: int = 10) -> List[MatchResult]:
    """
    Orchestrates the full co-founder matching workflow.
    """
    # 1. Parse idea
    requirements = parse_user_idea(idea_text)
    
    # 2. Fetch profiles from all sources
    # For now, we'll use mock queries
    queries = requirements.required_skills + [requirements.domain]
    github_profiles = fetch_github_profiles(queries)
    dataset_profiles = fetch_founder_datasets()
    
    all_profiles = merge_and_clean_profiles([github_profiles, dataset_profiles])
    
    # 3. Rank profiles
    # engine = CofounderMatchingEngine() # TODO: Initialize properly
    # ranked_matches = engine.rank_profiles(requirements, all_profiles)
    
    # MOCK IMPLEMENTATION until model is integrated
    ranked_matches = [
        MatchResult(
            profile=p,
            match_score=0.85 - (i * 0.1),
            domain_fit=True,
            why_matched="Strong skill and domain overlap (mocked).",
            intro_message=f"Hi {p.name.split()[0]}, I saw your profile and thought your skills in {p.skills[0]} would be a great fit for my new {requirements.domain} startup. Let's connect."
        ) for i, p in enumerate(all_profiles)
    ]

    return ranked_matches[:top_k]

