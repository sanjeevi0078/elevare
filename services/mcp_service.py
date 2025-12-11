import os
import json
import logging
import random
from typing import Any, Dict, Tuple

import requests
import redis
from pytrends.request import TrendReq

from models.idea_model import RefinedIdea, MarketViabilityProfile
from config import settings

logger = logging.getLogger(__name__)

# Pytrends client (does not require an API key)
TRENDS_CLIENT = TrendReq(hl="en-US", tz=360)


def get_redis_client() -> redis.Redis:
    """Get a Redis client instance."""
    return redis.from_url(settings.REDIS_URL)


class MarketProfilingService:
    """Minimum Concept Profiling (MCP) service.

    Responsibilities:
    - Market fencing via Redis cache (deterministic cache keys)
    - Fetching external market signals (simulated for MVP)
    - Proprietary viability scoring
    """

    def __init__(self, redis_client: redis.Redis | None = None):
        # Initialize or accept an existing Redis client
        if redis_client is None:
            self.redis = redis.from_url(settings.REDIS_URL)
        else:
            self.redis = redis_client

    def _generate_cache_key(self, domain: str, location: str) -> str:
        """Generate a deterministic cache key for market fencing.

        Format: f"MCP:{domain.upper()}:{location.upper()}"
        """

        domain_part = (domain or "OTHER").upper()
        location_part = (location or "GLOBAL").upper()
        return f"MCP:{domain_part}:{location_part}"

    def _get_country_code(self, location: str | None) -> str:
        """Map a free-form location string to a two-letter country code for pytrends.

        Returns an empty string for worldwide if no match is found.
        """
        if not location:
            return ""
        location_map = {
            "india": "IN",
            "bangalore": "IN",
            "bengaluru": "IN",
            "london": "GB",
            "united kingdom": "GB",
            "uk": "GB",
            "usa": "US",
            "united states": "US",
            "seattle": "US",
            "paris": "FR",
            "france": "FR",
            "germany": "DE",
        }
        lower = location.lower()
        for key, code in location_map.items():
            if key in lower:
                return code
        return ""

    def _fetch_external_data(self, domain: str, location: str) -> Dict[str, Any]:
        """Fetch Google Trends interest and estimate competitor count.

        Uses pytrends to compute an average interest over the last 12 months for
        the given domain keyword, normalized to 0.0–1.0. Competitor count remains
        a light heuristic until a real SERP provider is integrated.
        """

        keyword = (domain or "").strip() or "startup"
        geo_code = self._get_country_code(location)

        raw_trend_score: float = 0.0
        try:
            TRENDS_CLIENT.build_payload(
                kw_list=[keyword],
                cat=0,
                timeframe="today 12-m",
                geo=geo_code,
                gprop="",
            )
            df = TRENDS_CLIENT.interest_over_time()
            if not df.empty and keyword in df.columns:
                avg_interest = float(df[keyword].mean())
                raw_trend_score = round(max(0.0, min(1.0, avg_interest / 100.0)), 1)
            else:
                logger.info("Pytrends returned empty data for keyword=%s geo=%s", keyword, geo_code)
        except Exception:
            logger.exception("Pytrends fetch failed; defaulting trend score to 0.0")

        # Competitor analysis
        raw_competitor_count = 0
        
        if settings.SERP_API_KEY:
            try:
                # Example using SerpApi
                params = {
                    "engine": "google",
                    "q": f"site:crunchbase.com {domain} {keyword}",
                    "api_key": settings.SERP_API_KEY
                }
                resp = requests.get("https://serpapi.com/search", params=params, timeout=10)
                if resp.status_code == 200:
                    results = resp.json()
                    # Count organic results as proxy for competitors
                    # Multiply by factor to estimate total market
                    raw_competitor_count = len(results.get("organic_results", [])) * 3
            except Exception as e:
                logger.error(f"SERP API failed: {e}")
        
        # Fallback heuristic if no API key or failure (only in dev)
        if raw_competitor_count == 0 and settings.is_development:
            try:
                base = 60 if domain in {"Fintech", "SaaS"} else 25
                jitter = random.randint(-10, 10)
                raw_competitor_count = max(0, base + jitter)
            except Exception:
                raw_competitor_count = 0

        return {
            "raw_trend_score": raw_trend_score,
            "raw_competitor_count": raw_competitor_count,
        }

    def _calculate_viability_score(self, raw_data: Dict[str, Any]) -> Tuple[float, str]:
        """Proprietary scoring: Score = (Trend * 0.6) + (CompetitionBonus * 0.4).

        CompetitionBonus = max(0, 50 - competitor_count) / 10.0
        Caps: ensure final score within 0.0 - 5.0
        Returns (score, rationale)
        """

        trend = float(raw_data.get("raw_trend_score", 0.0))
        competitors = int(raw_data.get("raw_competitor_count", 0))

        competition_bonus = max(0, 50 - competitors) / 10.0

        raw_score = (trend * 0.6) + (competition_bonus * 0.4)
        final_score = max(0.0, min(5.0, round(raw_score, 1)))

        rationale = (
            f"Trend({trend})*0.6 + CompetitionBonus({competition_bonus})*0.4 => {final_score}. "
            f"Competitors={competitors}."
        )

        return final_score, rationale

    def get_concept_profile(self, refined_idea: RefinedIdea) -> MarketViabilityProfile:
        """Main entrypoint: produce a MarketViabilityProfile for a RefinedIdea.

        Flow:
        - Check cache
        - If miss, fetch external data, calculate score, construct profile, cache it
        - On any failure, return a zeroed profile with rationale
        """

        domain = refined_idea.core_domain
        location = refined_idea.suggested_location or "GLOBAL"
        cache_key = self._generate_cache_key(domain, location)

        # 1) Cache check
        try:
            cached = self.redis.get(cache_key)
            if cached:
                try:
                    payload = json.loads(cached)
                    profile = MarketViabilityProfile.model_validate(payload)
                    return profile
                except Exception:
                    # Fall through to regen if cache is corrupted
                    logger.warning("Cache hit but failed to deserialize profile; regenerating.")
        except Exception as e:
            logger.exception("Redis error during cache check")

        # 2) Fetch external data
        try:
            raw_data = self._fetch_external_data(domain, location)
        except Exception as e:
            logger.exception("Failed to fetch external data")
            return MarketViabilityProfile.model_validate(
                {
                    "idea_title": refined_idea.idea_title,
                    "core_domain": domain,
                    "suggested_location": refined_idea.suggested_location,
                    "market_viability_score": 0.0,
                    "community_engagement_score": 0.0,
                    "rationale": f"External data fetch failed: {e}",
                    "raw_trend_score": None,
                    "raw_competitor_count": None,
                }
            )

        # 3) Score calculation
        try:
            score, rationale = self._calculate_viability_score(raw_data)
        except Exception as e:
            logger.exception("Scoring error")
            return MarketViabilityProfile.model_validate(
                {
                    "idea_title": refined_idea.idea_title,
                    "core_domain": domain,
                    "suggested_location": refined_idea.suggested_location,
                    "market_viability_score": 0.0,
                    "community_engagement_score": 0.0,
                    "rationale": f"Scoring failed: {e}",
                    "raw_trend_score": raw_data.get("raw_trend_score"),
                    "raw_competitor_count": raw_data.get("raw_competitor_count"),
                }
            )

        # 4) Construct profile
        profile = MarketViabilityProfile.model_validate(
            {
                "idea_title": refined_idea.idea_title,
                "core_domain": domain,
                "suggested_location": refined_idea.suggested_location,
                "market_viability_score": score,
                "community_engagement_score": 0.0,
                "rationale": rationale,
                "raw_trend_score": raw_data.get("raw_trend_score"),
                "raw_competitor_count": raw_data.get("raw_competitor_count"),
            }
        )

        # 5) Cache write
        try:
            serialized = json.dumps(profile.model_dump())
            # 24 hours
            self.redis.set(cache_key, serialized, ex=86400)
        except Exception:
            logger.exception("Failed to write profile to Redis cache; continuing without cache.")

        return profile


__all__ = ["MarketProfilingService"]
