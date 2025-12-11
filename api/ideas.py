import json
import time
from typing import List, Optional, Any, Dict

import redis
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from config import settings
from logger import logger
from exceptions import RedisError, IdeaNotFoundError
from models.idea_model import FullIdeaProfile

router = APIRouter(tags=["ideas"])


def get_redis() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL)


class IdeaRecord(BaseModel):
    id: int
    created_at: float
    user_id: str | None = None
    refined_idea: Dict[str, Any]
    market_profile: Dict[str, Any]
    overall_confidence_score: float
    likes: int = 0


class PublicIdea(BaseModel):
    """Simplified idea for public display on the Idea Wall."""
    id: int
    title: str
    description: str
    category: str
    user_id: int | None = None
    user_name: str | None = None
    likes: int = 0
    created_at: str
    tags: List[str] = []
    status: str = "published"


class PublicIdeasResponse(BaseModel):
    """Response for the public ideas endpoint."""
    ideas: List[PublicIdea]
    total: int
    page: int
    per_page: int


@router.post("/", response_model=IdeaRecord)
def create_idea(profile: FullIdeaProfile, user_id: str | None = None, r: redis.Redis = Depends(get_redis)) -> IdeaRecord:
    try:
        new_id = int(r.incr("ideas:seq"))
        record = {
            "id": new_id,
            "created_at": time.time(),
            "user_id": user_id,
            # Ensure plain dicts for storage
            "refined_idea": getattr(profile.refined_idea, "model_dump", lambda: profile.refined_idea)(),
            "market_profile": getattr(profile.market_profile, "model_dump", lambda: profile.market_profile)(),
            "overall_confidence_score": float(profile.overall_confidence_score),
            "likes": 0,
        }
        r.set(f"ideas:{new_id}", json.dumps(record))
        r.lpush("ideas:list", new_id)
        logger.info(f"Created new idea with ID: {new_id}", extra={"user_id": user_id})
        return IdeaRecord(**record)
    except Exception as e:
        logger.error(f"Failed to save idea: {e}", exc_info=True)
        raise RedisError(message="Failed to save idea", original_error=e)


@router.get("/", response_model=List[IdeaRecord])
def list_ideas(limit: int = 20, user_id: str | None = None, r: redis.Redis = Depends(get_redis)) -> List[IdeaRecord]:
    try:
        ids = [int(x) for x in r.lrange("ideas:list", 0, max(0, limit - 1))]
        out: List[IdeaRecord] = []
        for i in ids:
            raw = r.get(f"ideas:{i}")
            if not raw:
                continue
            data = json.loads(raw)
            if user_id is None or data.get("user_id") == user_id:
                out.append(IdeaRecord(**data))
        return out
    except Exception as e:
        logger.error(f"Failed to list ideas: {e}", exc_info=True)
        raise RedisError(message="Failed to list ideas", original_error=e)


@router.get("/public", response_model=PublicIdeasResponse)
def get_public_ideas(
    page: int = 1,
    per_page: int = 20,
    r: redis.Redis = Depends(get_redis)
) -> PublicIdeasResponse:
    """
    Get public ideas for the Global Idea Wall.
    Returns simplified idea data for frontend display.
    """
    try:
        start = (page - 1) * per_page
        end = start + per_page - 1
        
        ids = [int(x) for x in r.lrange("ideas:list", start, end)]
        total = r.llen("ideas:list")
        
        public_ideas: List[PublicIdea] = []
        for idea_id in ids:
            raw = r.get(f"ideas:{idea_id}")
            if not raw:
                continue
            
            data = json.loads(raw)
            refined = data.get("refined_idea", {})
            
            # Extract title and description from refined_idea
            title = refined.get("refined_title", refined.get("title", f"Idea #{idea_id}"))
            description = refined.get("vision_statement", refined.get("description", ""))
            category = refined.get("industry", refined.get("category", "Technology"))
            
            # Extract tags from key_differentiators or other fields
            tags = refined.get("key_differentiators", [])
            if isinstance(tags, str):
                tags = [tags]
            
            public_ideas.append(PublicIdea(
                id=idea_id,
                title=title,
                description=description,
                category=category,
                user_id=int(data.get("user_id")) if data.get("user_id") else None,
                user_name=None,  # Could be fetched from users table
                likes=data.get("likes", 0),
                created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(data.get("created_at", 0))),
                tags=tags[:5] if tags else [],
                status="published"
            ))
        
        return PublicIdeasResponse(
            ideas=public_ideas,
            total=total,
            page=page,
            per_page=per_page
        )
        
    except Exception as e:
        logger.error(f"Failed to get public ideas: {e}", exc_info=True)
        raise RedisError(message="Failed to get public ideas", original_error=e)


@router.post("/{idea_id}/like")
def like_idea(idea_id: int, r: redis.Redis = Depends(get_redis)) -> Dict[str, Any]:
    """
    Like an idea. Increments the like count.
    Returns the updated like count.
    """
    raw = r.get(f"ideas:{idea_id}")
    if not raw:
        raise IdeaNotFoundError(idea_id=idea_id)
    
    data = json.loads(raw)
    data["likes"] = data.get("likes", 0) + 1
    r.set(f"ideas:{idea_id}", json.dumps(data))
    
    logger.info(f"Idea {idea_id} liked. Total likes: {data['likes']}")
    
    return {"id": idea_id, "likes": data["likes"], "success": True}


@router.get("/{idea_id}", response_model=IdeaRecord)
def get_idea(idea_id: int, r: redis.Redis = Depends(get_redis)) -> IdeaRecord:
    raw = r.get(f"ideas:{idea_id}")
    if not raw:
        raise IdeaNotFoundError(idea_id=idea_id)
    data = json.loads(raw)
    return IdeaRecord(**data)
