"""GitHub Profile Harvester
================================
Async utility for retrieving real developer profiles relevant
to a startup idea or domain. Provides lightweight relevance scoring
without heavy ML dependencies.

Uses:
- Search users by keyword/domain
- Hydrates user details + repos
- Computes a heuristic relevance score

To keep API calls efficient for demo/MVP usage:
- Limits repos per user
- Avoids topic API extra calls (preview header)
- Provides graceful degradation on rate limiting
"""
from __future__ import annotations
import os
import asyncio
import httpx
from typing import List, Dict, Any, Optional

GITHUB_API_URL = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_API_TOKEN")  # Optional

class GitHubProfile:
    def __init__(self, raw_user: Dict[str, Any], details: Dict[str, Any], repos: List[Dict[str, Any]], relevance: float, match_score: int):
        self.id = raw_user.get("id")
        self.username = raw_user.get("login")
        self.name = details.get("name") or raw_user.get("login")
        self.avatar_url = details.get("avatar_url")
        self.profile_url = details.get("html_url")
        self.location = details.get("location") or "Remote"
        self.bio = details.get("bio") or "Open source contributor."\
        
        # Derived
        self.repos = [
            {
                "name": r.get("name"),
                "url": r.get("html_url"),
                "description": r.get("description"),
                "language": r.get("language"),
                "stargazers": r.get("stargazers_count", 0)
            } for r in repos
        ]
        self.skills = self._derive_skills(repos)
        self.relevance = relevance
        self.match_score = match_score
        self.source = "github"
        self.role_type = "Technical Co-Founder" if relevance > 1.2 else "Engineer"
        self.interests: List[str] = []

    def _derive_skills(self, repos: List[Dict[str, Any]]) -> List[str]:
        langs = []
        for r in repos:
            lang = r.get("language")
            if lang and lang not in langs:
                langs.append(lang)
        if not langs:
            langs.append("Open Source")
        return langs[:8]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "name": self.name,
            "username": self.username,
            "avatar_url": self.avatar_url,
            "profile_url": self.profile_url,
            "location": self.location,
            "bio": self.bio,
            "skills": self.skills,
            "interests": self.interests,
            "match_percentage": self.match_score,
            "role_type": self.role_type,
            "synergy_analysis": f"Relevant repos & languages align with target domain. Relevance factor {self.relevance:.2f}.",
            "missing_skills_filled": self.skills[:4],
            "recommended_action": "Must Connect" if self.match_score >= 85 else ("Strong Option" if self.match_score >= 70 else "Explore"),
            "intro_message": f"Hi {self.name.split()[0]}, impressed by your work on {self.repos[0]['name'] if self.repos else 'your projects'}. Building something related and think there's strong synergy—open to a quick chat?",
            "source": self.source
        }

class GitHubProfileHarvester:
    def __init__(self, per_user_repos: int = 20, users_limit: int = 5):
        self.per_user_repos = per_user_repos
        self.users_limit = users_limit

    async def search_users(self, query: str) -> List[Dict[str, Any]]:
        params = {"q": query, "per_page": self.users_limit}
        headers = {"Accept": "application/vnd.github+json"}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{GITHUB_API_URL}/search/users", params=params, headers=headers)
            if resp.status_code != 200:
                return []
            data = resp.json()
            return data.get("items", [])

    async def _hydrate_user(self, client: httpx.AsyncClient, raw_user: Dict[str, Any], domain_keywords: List[str]) -> Optional[GitHubProfile]:
        headers = {"Accept": "application/vnd.github+json"}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

        details_resp = await client.get(raw_user.get("url"), headers=headers)
        if details_resp.status_code != 200:
            return None
        details = details_resp.json()

        repos_resp = await client.get(raw_user.get("repos_url"), params={"per_page": self.per_user_repos}, headers=headers)
        repos = repos_resp.json() if repos_resp.status_code == 200 else []

        # Relevance heuristic
        relevance_hits = 0
        for r in repos:
            text = (r.get("name", "") + " " + (r.get("description") or "")).lower()
            if any(k in text for k in domain_keywords):
                relevance_hits += 1
        total = max(1, len(repos))
        relevance = (relevance_hits * 2 + total * 0.3) / total  # weighted
        match_score = min(95, max(55, int(70 + relevance * 20)))
        return GitHubProfile(raw_user, details, repos, relevance, match_score)

    async def harvest(self, idea_text: str, domain_hint: str) -> List[Dict[str, Any]]:
        # Extract simple keywords
        keywords = [w.lower() for w in domain_hint.split() if len(w) > 3][:4]
        query = "+".join(keywords) if keywords else domain_hint
        raw_users = await self.search_users(query)
        if not raw_users:
            return []
        headers = {"Accept": "application/vnd.github+json"}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
        async with httpx.AsyncClient(timeout=20) as client:
            tasks = [self._hydrate_user(client, u, keywords) for u in raw_users]
            results = await asyncio.gather(*tasks)
        profiles = [p.to_dict() for p in results if p]
        return profiles

__all__ = ["GitHubProfileHarvester"]
