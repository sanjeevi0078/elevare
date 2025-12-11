"""
AI-Powered Event Discovery
Uses live web search + LLM to find personalized startup events
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["events"])

# Lazy initialization to avoid import errors when API keys not set
scout = None

def get_scout():
    """Lazy load EventScout service"""
    global scout
    if scout is None:
        from services.event_scout import EventScout
        scout = EventScout()
    return scout

class EventRequest(BaseModel):
    """Request model for event discovery"""
    interest: str = "Technology"
    location: str = "Global"
    stage: str = "early"  # early, growth, scale


@router.post("/discover")
def discover_events(req: EventRequest):
    """
    Discover personalized startup events using live web search + AI
    
    Args:
        req: EventRequest with interest (domain), location, and stage
        
    Returns:
        Dictionary with "events" array containing:
        - title, category, date, location, description, price, url, tag
        
    Example:
        POST /events/discover
        {
            "interest": "HealthTech",
            "location": "London",
            "stage": "early"
        }
    """
    try:
        logger.info(f"🔍 Event discovery requested: {req.interest} in {req.location} (stage: {req.stage})")
        
        # Get scout instance
        event_scout = get_scout()
        
        # Find events using the Event Scout
        # TODO: Add Redis caching with 24h TTL to save API costs
        # cache_key = f"events:{req.interest}:{req.location}:{req.stage}"
        
        data = event_scout.find_events(
            interest=req.interest,
            location=req.location,
            stage=req.stage
        )
        
        event_count = len(data.get("events", []))
        logger.info(f"✅ Returning {event_count} events for {req.interest} in {req.location}")
        
        return data
        
    except Exception as e:
        logger.error(f"❌ Event discovery failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to discover events: {str(e)}"
        )


@router.get("/health")
def health_check():
    """Check if event scout service is configured"""
    import os
    
    has_groq = bool(os.getenv("GROQ_API_KEY"))
    has_serp = bool(os.getenv("SERP_API_KEY"))
    
    return {
        "status": "healthy" if (has_groq and has_serp) else "degraded",
        "groq_configured": has_groq,
        "serp_configured": has_serp,
        "message": "Event Scout is ready" if (has_groq and has_serp) else "Missing API keys"
    }
