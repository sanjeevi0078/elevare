"""Async Event Scout Generator
Generates context-aware, realistic upcoming events aligned to a user's startup idea.
Rather than relying on flaky API searches, it produces tailored event suggestions
with strong narrative relevance. Falls back to deterministic templates if LLM fails.
"""
from __future__ import annotations
import os
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from groq import Groq  # type: ignore

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

FALLBACK_EVENTS = [
    {
        "title": "Global Founder Catalyst Summit 2025",
        "date": "Feb 12-14, 2025",
        "location": "Virtual",
        "type": "Conference",
        "relevance": "High-density networking + investors scouting AI-enabled innovation."
    },
    {
        "title": "NextGen Innovation Hack Weekend",
        "date": "Mar 1-2, 2025",
        "location": "Bangalore, India",
        "type": "Hackathon",
        "relevance": "Ideal for rapid prototyping + recruiting technical collaborators."
    },
    {
        "title": "Strategic Venture Pitch Forum",
        "date": "Apr 18, 2025",
        "location": "San Francisco, CA",
        "type": "Summit",
        "relevance": "Focused investor roundtables for domain-specific ventures."
    }
]

class AsyncEventScout:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

    def _prompt(self, idea_text: str) -> str:
        today = datetime.utcnow().strftime("%B %d, %Y")
        return f"""
Act as a founder-focused Event Intelligence Engine. Today is {today}.
Startup Idea: "{idea_text}"
Generate EXACTLY 5 high-signal upcoming events (Hackathon | Conference | Summit) occurring in the next 9 months.
They must sound realistic, non-generic, and contain implicit strategic alignment to the idea.

Return ONLY JSON array matching schema:
[
  {{"title":"Event Name","date":"Readable Future Date","location":"City, Country or Virtual","type":"Hackathon|Conference|Summit","relevance":"One sentence: Why strategically relevant."}}
]
Rules:
- Prefer a geographic mix (Asia, Europe, US, Virtual) unless idea is geo-specific.
- Avoid filler words. Keep relevance sentence punchy.
- Dates must look plausible for 2025.
- No markdown, no commentary—ONLY JSON.
""".strip()

    async def generate(self, idea_text: str) -> List[Dict[str, Any]]:
        if not self.client:
            return FALLBACK_EVENTS
        prompt = self._prompt(idea_text)
        try:
            # Run sync LLM call in thread to avoid blocking event loop
            resp = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.55,
                max_tokens=1200
            )
            content = resp.choices[0].message.content.strip()
            data = json.loads(content)
            if isinstance(data, dict):
                # Sometimes the model returns {"events": [...]} variant
                data = data.get("events", [])
            cleaned = []
            for e in data[:5]:
                cleaned.append({
                    "title": e.get("title"),
                    "date": e.get("date"),
                    "location": e.get("location"),
                    "type": e.get("type"),
                    "relevance": e.get("relevance")
                })
            return cleaned or FALLBACK_EVENTS
        except Exception:
            return FALLBACK_EVENTS

__all__ = ["AsyncEventScout"]
