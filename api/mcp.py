import json
import logging
from typing import Any

from fastapi import APIRouter, Depends
import redis

from config import settings
from logger import logger
from exceptions import RedisError, ExternalServiceError
from models.idea_model import RefinedIdea, MarketViabilityProfile
from services.mcp_service import MarketProfilingService

# logger = logging.getLogger(__name__) # Use centralized logger

router = APIRouter(prefix="/mcp", tags=["mcp"])


def get_redis() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL)


def get_mcp_service(r: redis.Redis = Depends(get_redis)) -> MarketProfilingService:
    return MarketProfilingService(redis_client=r)


@router.post("/profile", response_model=MarketViabilityProfile)
def get_profile(refined: RefinedIdea, svc: MarketProfilingService = Depends(get_mcp_service)) -> MarketViabilityProfile:
    try:
        return svc.get_concept_profile(refined)
    except Exception as e:
        logger.error(f"Failed to compute market profile: {e}", exc_info=True)
        raise ExternalServiceError(service_name="MCP Service", message="Failed to compute market profile", original_error=e)


@router.get("/cache-key")
def cache_key(domain: str, location: str | None = None, svc: MarketProfilingService = Depends(get_mcp_service)):
    try:
        key = svc._generate_cache_key(domain, location or "GLOBAL")
        return {"cache_key": key}
    except Exception as e:
        logger.error(f"Failed to generate cache key: {e}", exc_info=True)
        raise RedisError(message="Failed to generate cache key", original_error=e)


@router.get("/status")
def mcp_status(r: redis.Redis = Depends(get_redis)):
    """Report Redis health and approximate cache size for MCP keys.

    Returns JSON with: reachable (bool), db (int), key_count (int), sample_keys (list).
    """
    try:
        pong = r.ping()
        # Attempt to count keys with a conservative scan to avoid blocking
        pattern = "mcp:*"
        total = 0
        sample = []
        cursor = 0
        for _ in range(5):  # up to 5 scan rounds
            cursor, keys = r.scan(cursor=cursor, match=pattern, count=200)
            total += len(keys)
            if len(sample) < 5:
                sample.extend([k.decode("utf-8") if isinstance(k, bytes) else k for k in keys[:5 - len(sample)]])
            if cursor == 0:
                break
        return {
            "reachable": bool(pong),
            "db": r.connection_pool.connection_kwargs.get("db", 0),
            "key_count": total,
            "sample_keys": sample,
        }
    except Exception as e:
        logger.exception("MCP status error")
        return {"reachable": False, "error": str(e)}
