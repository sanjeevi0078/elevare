from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session

from config import settings
from logger import logger
from exceptions import DatabaseError, UserNotFoundError, ExternalServiceError
from db.database import get_db
from models.user_models import User
from services.matching_service import MatchingService
from services.cofounder_matching_engine import get_smart_matches, AIMatchResult

router = APIRouter(tags=["matching"])

# --- User CRUD Models ---
class UserCreate(BaseModel):
    name: str
    email: str
    location: Optional[str] = None
    interest: Optional[str] = None
    personality: Optional[str] = None
    commitment_level: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    skills: Optional[List[str]] = None

class SkillOut(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    location: Optional[str]
    interest: Optional[str]
    personality: Optional[str]
    commitment_level: Optional[float]
    skills: List[SkillOut] = []
    model_config = ConfigDict(from_attributes=True)


class MatchOut(BaseModel):
    user: UserOut
    score: float

# --- User Endpoints ---
@router.post("/users", response_model=UserOut)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> UserOut:
    svc = MatchingService(db)
    try:
        return svc.create_user(
            name=payload.name,
            email=payload.email,
            location=payload.location,
            interest=payload.interest,
            personality=payload.personality,
            commitment_level=payload.commitment_level,
            skills=payload.skills or [],
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create user: {e}", exc_info=True)
        raise DatabaseError(message="Failed to create user", original_error=e)


@router.get("/users", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db)) -> List[UserOut]:
    svc = MatchingService(db)
    return svc.list_users()

@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)) -> UserOut:
    """Fetch a single user profile.

    Added to support frontend match detail modals without pulling all users.
    """
    svc = MatchingService(db)
    user = svc.get_user(user_id)
    if not user:
        raise UserNotFoundError(user_id=user_id)
    return user


@router.get("/matches/{user_id}", response_model=List[MatchOut])
def get_matches(user_id: int, limit: int = 20, db: Session = Depends(get_db)) -> List[MatchOut]:
    svc = MatchingService(db)
    pairs = svc.get_matches(user_id, limit=limit)
    return [{"user": u, "score": s} for (u, s) in pairs]


# ============================================================================
# AI HEADHUNTER MATCHING
# ============================================================================

class IdeaMatchRequest(BaseModel):
    idea_text: str = Field(..., min_length=10)
    top_k: int = Field(default=10)
    exclude_user_id: Optional[int] = None  # Exclude current user from results


class AICofounderMatchResponse(BaseModel):
    """Enriched Response with Real Profile Data"""
    id: str
    name: Optional[str]
    username: Optional[str] = None
    skills: List[str]
    interests: List[str]
    bio: Optional[str]
    location: Optional[str]
    
    # AI Analysis
    match_percentage: float
    role_type: str
    synergy_analysis: str
    missing_skills_filled: List[str]
    recommended_action: str
    intro_message: str
    
    # Real Data Fields
    avatar_url: Optional[str] = None
    profile_url: Optional[str] = None
    source: str  # 'local' or 'github'


class HybridProfileOut(BaseModel):
    """Unified hybrid profile including technical (GitHub/local) and synthetic personas."""
    id: Optional[str] = None  # synthetic may omit
    name: str
    username: Optional[str] = None
    role_type: str
    bio: Optional[str]
    skills: List[str] = []
    interests: List[str] = []
    top_strengths: List[str] = []
    strategic_value: Optional[str] = None
    location: Optional[str] = None
    match_percentage: int
    synergy_analysis: str
    recommended_action: str
    intro_message: str
    avatar_url: Optional[str] = None
    profile_url: Optional[str] = None
    source: str  # 'github' | 'local' | 'synthetic'
    missing_skills_filled: List[str] = []

class ProfileCard(BaseModel):
    name: str
    role: str
    location: Optional[str] = None
    bio: Optional[str] = None
    image: Optional[str] = None
    match_score: int
    must_connect: bool
    match_reason: str
    skills: List[str] = []
    github_url: Optional[str] = None
    source: str

class HybridProfilesEnvelope(BaseModel):
    profiles: List[ProfileCard]

class EventOut(BaseModel):
    title: str
    date: str
    location: str
    type: str
    relevance: str

class ConnectInviteRequest(BaseModel):
    profile_name: str
    user_idea: Optional[str] = None
    medium: Optional[str] = Field(default="internal")  # could be 'internal' | 'email' | 'github'

class ConnectInviteResponse(BaseModel):
    status: str
    profile_name: str
    latency_ms: int
    message_preview: Optional[str] = None

class OutreachDraftRequest(BaseModel):
    user_role: str
    profile_role: str
    profile_name: str
    profile_bio: Optional[str] = None
    user_idea: str

class OutreachDraftResponse(BaseModel):
    draft_message: str
    tokens_used: Optional[int] = None




@router.post("/find-cofounders", response_model=List[AICofounderMatchResponse])
def find_cofounders_by_idea(request: IdeaMatchRequest, db: Session = Depends(get_db)):
    """
    AI Headhunter Endpoint:
    1. Analyzes Idea
    2. Searches Real GitHub Users + Local DB
    3. Returns AI-Graded Candidates (excluding the requesting user)
    """
    try:
        matches = get_smart_matches(
            request.idea_text, 
            db, 
            request.top_k,
            exclude_user_id=request.exclude_user_id
        )
        
        results = []
        for m in matches:
            results.append(AICofounderMatchResponse(
                id=m.id,
                name=m.name,
                username=m.username,
                skills=m.skills or [],
                interests=m.interests or [],
                bio=m.bio,
                location=m.location,
                match_percentage=m.match_percentage,
                role_type=m.role_type,
                synergy_analysis=m.synergy_analysis,
                missing_skills_filled=m.missing_skills_filled,
                recommended_action=m.recommended_action,
                intro_message=m.intro_message,
                avatar_url=m.avatar_url,
                profile_url=m.profile_url,
                source=m.source
            ))
        return results
        
    except Exception as e:
        logger.error(f"Matching failed: {e}", exc_info=True)
        raise ExternalServiceError(service_name="Matching Engine", message=str(e))


@router.post("/hybrid-profiles", response_model=HybridProfilesEnvelope)
def get_hybrid_profiles(request: IdeaMatchRequest, db: Session = Depends(get_db)) -> HybridProfilesEnvelope:
    """Return a merged list of real technical profiles (GitHub + local DB) and synthetic business/operations/medical personas.

    Steps:
    1. Get smart technical matches (local + GitHub) via existing engine.
    2. Harvest additional GitHub profiles directly (broad search) if technical pool < request.top_k.
    3. Generate synthetic complementary non-technical personas.
    4. Merge, de-duplicate by username/name, prioritize higher match percentages.
    """
    from services.github_profile_harvester import GitHubProfileHarvester
    from services.synthetic_profile_generator import SyntheticProfileGenerator

    try:
        # 1. Existing smart matches (technical + maybe GitHub)
        technical_matches = get_smart_matches(
            request.idea_text,
            db,
            request.top_k,
            exclude_user_id=request.exclude_user_id
        )

        hybrid: List[HybridProfileOut] = []
        for m in technical_matches:
            hybrid.append(HybridProfileOut(
                id=m.id,
                name=m.name or m.username or "Unknown",
                username=m.username,
                role_type=m.role_type,
                bio=m.bio,
                skills=m.skills or [],
                interests=m.interests or [],
                top_strengths=[],
                strategic_value=None,
                location=m.location,
                match_percentage=int(m.match_percentage),
                synergy_analysis=m.synergy_analysis,
                recommended_action=m.recommended_action,
                intro_message=m.intro_message,
                avatar_url=m.avatar_url,
                profile_url=m.profile_url,
                source=m.source,
                missing_skills_filled=m.missing_skills_filled or []
            ))

        # 2. Direct GitHub harvest if below target
        domain_hint = request.idea_text.split(" ")[0:5]
        domain_hint_str = " ".join(domain_hint)
        if len(technical_matches) < request.top_k:
            harvester = GitHubProfileHarvester(users_limit=max(3, request.top_k - len(technical_matches)))
            harvested = []
            try:
                # NOTE: harvest is async; run in loop
                import asyncio
                harvested = asyncio.run(harvester.harvest(request.idea_text, domain_hint_str))
            except RuntimeError:
                # If already in loop (e.g., called inside async context), create task differently
                loop = asyncio.get_event_loop()
                harvested = loop.run_until_complete(harvester.harvest(request.idea_text, domain_hint_str))
            for h in harvested:
                hybrid.append(HybridProfileOut(
                    id=h.get("id"),
                    name=h.get("name"),
                    username=h.get("username"),
                    role_type=h.get("role_type"),
                    bio=h.get("bio"),
                    skills=h.get("skills", []),
                    interests=h.get("interests", []),
                    top_strengths=[],
                    strategic_value=None,
                    location=h.get("location"),
                    match_percentage=int(h.get("match_percentage", 70)),
                    synergy_analysis=h.get("synergy_analysis", "Relevant technical alignment."),
                    recommended_action=h.get("recommended_action", "Explore"),
                    intro_message=h.get("intro_message", "Hi there — exploring synergy."),
                    avatar_url=h.get("avatar_url"),
                    profile_url=h.get("profile_url"),
                    source=h.get("source", "github"),
                    missing_skills_filled=h.get("missing_skills_filled", [])
                ))

        # 3. Synthetic complementary personas
        generator = SyntheticProfileGenerator(max_profiles=5)
        synthetic_profiles = generator.generate(request.idea_text, domain_hint_str)
        for s in synthetic_profiles:
            hybrid.append(HybridProfileOut(
                name=s.get("name"),
                role_type=s.get("role_type"),
                bio=s.get("bio"),
                skills=[],
                interests=[],
                top_strengths=s.get("top_strengths", []),
                strategic_value=s.get("strategic_value"),
                location=None,
                match_percentage=int(s.get("match_percentage", 68)),
                synergy_analysis=s.get("synergy_analysis", "Complements technical team."),
                recommended_action=s.get("recommended_action", "Explore"),
                intro_message=s.get("intro_message", "Hi — potential synergy?"),
                avatar_url=None,
                profile_url=None,
                source="synthetic",
                missing_skills_filled=[]
            ))

        # 4. De-duplicate by (username or name)
        seen = set()
        unique: List[HybridProfileOut] = []
        for p in hybrid:
            key = (p.username or p.name).lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(p)

        # 5. Sort by match percentage desc
        unique.sort(key=lambda x: x.match_percentage, reverse=True)

        # Map to frontend schema
        profiles_payload = []
        for p in unique[: request.top_k + 5]:
            # Determine source normalization (synthetic -> ai)
            normalized_source = 'ai' if p.source == 'synthetic' else ('github' if p.source == 'github' else 'ai')
            match_score = p.match_percentage
            must_connect = (match_score >= 90) or (p.recommended_action.lower() == 'must connect')
            # Merge skills + strengths (avoid duplicates)
            combined_skills = []
            for s in (p.skills or []) + (p.top_strengths if hasattr(p, 'top_strengths') else []):
                if s and s not in combined_skills:
                    combined_skills.append(s)
            profiles_payload.append(ProfileCard(
                name=p.name,
                role=p.role_type,
                location=p.location,
                bio=p.bio,
                image=p.avatar_url or (f"https://ui-avatars.com/api/?name={p.name.replace(' ', '+')}&background=random" if p.name else None),
                match_score=match_score,
                must_connect=must_connect,
                match_reason=p.synergy_analysis,
                skills=combined_skills,
                github_url=p.profile_url if p.source == 'github' else None,
                source=normalized_source
            ))

        return HybridProfilesEnvelope(profiles=profiles_payload)
    except Exception as e:
        logger.error(f"Hybrid profile generation failed: {e}", exc_info=True)
        raise ExternalServiceError(service_name="HybridMatching", message=str(e))


class EventScoutRequest(BaseModel):
    idea_text: str = Field(..., min_length=8)

@router.post("/event-scout", response_model=List[EventOut])
async def event_scout(request: EventScoutRequest) -> List[EventOut]:
    """Asynchronously generate context-aware upcoming events aligned to founder idea.

    Returns list of events with keys: title, date, location, type, relevance.
    """
    try:
        from services.event_scout_async import AsyncEventScout
        scout = AsyncEventScout()
        events = await scout.generate(request.idea_text)
        # Pydantic validation via EventOut
        return [EventOut(**e) for e in events]
    except Exception as e:
        logger.error(f"Event scout failed: {e}", exc_info=True)
        return []

@router.post("/connect-invite", response_model=ConnectInviteResponse)
def connect_invite(req: ConnectInviteRequest) -> ConnectInviteResponse:
    """Simulate sending a connection invite with small artificial latency.
    Frontend can call this to make the Connect button feel "alive".
    """
    import random, time
    start = time.time()
    # Simulated processing delay (jitter)
    time.sleep(random.uniform(0.4, 0.9))
    latency = int((time.time() - start) * 1000)
    preview = None
    if req.user_idea:
        preview = f"Hi {req.profile_name.split()[0]}, building something around '{req.user_idea[:60]}...' — would love to connect."[:160]
    return ConnectInviteResponse(status="sent", profile_name=req.profile_name, latency_ms=latency, message_preview=preview)

@router.post("/outreach-draft", response_model=OutreachDraftResponse)
def outreach_draft(req: OutreachDraftRequest) -> OutreachDraftResponse:
    """Generate a short (<=240 chars) personalized outreach draft using Groq.
    Falls back to deterministic template if rate-limited or error occurs.
    """
    import os, json
    from groq import Groq  # type: ignore
    api_key = os.getenv("GROQ_API_KEY")
    fallback = (
        f"Hi {req.profile_name.split()[0]}, your {req.profile_role.lower()} background aligns with our {req.user_role.lower()} driven approach to '{req.user_idea[:50]}'. Open to a quick chat?"
    )[:240]
    if not api_key:
        return OutreachDraftResponse(draft_message=fallback)
    prompt = f"""
Craft a concise (<240 chars) friendly founder outreach message.
From role: {req.user_role}
To role: {req.profile_role}
Target person: {req.profile_name}
Idea context: {req.user_idea}
Profile bio: {req.profile_bio}
Tone: Warm, credible, not salesy. Avoid hype words. Include a subtle compliment referencing bio.
Return ONLY the message text, no quotes.
""".strip()
    try:
        client = Groq(api_key=api_key)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=120
        )
        msg = completion.choices[0].message.content.strip()
        if len(msg) > 240:
            msg = msg[:237] + "..."
        usage = getattr(completion, 'usage', None)
        tokens_used = None
        if usage and hasattr(usage, 'total_tokens'):
            tokens_used = usage.total_tokens
        return OutreachDraftResponse(draft_message=msg, tokens_used=tokens_used)
    except Exception as e:
        logger.warning(f"Outreach draft fallback due to error: {e}")
        return OutreachDraftResponse(draft_message=fallback)

