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


@router.get("/{idea_id}", response_model=IdeaRecord)
def get_idea(idea_id: int, r: redis.Redis = Depends(get_redis)) -> IdeaRecord:
    raw = r.get(f"ideas:{idea_id}")
    if not raw:
        raise IdeaNotFoundError(idea_id=idea_id)
    data = json.loads(raw)
    return IdeaRecord(**data)
