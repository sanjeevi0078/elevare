"""Synthetic Profile Generator
Generates realistic non-technical cofounder personas (business, medical, operations)
to complement real technical GitHub profiles. Uses Groq LLM; falls back to deterministic
samples if LLM call fails or times out.
"""
from __future__ import annotations
import os
import json
import random
from typing import List, Dict, Any

from groq import Groq  # type: ignore

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

BUSINESS_ROLES = ["Growth Strategist", "Go-To-Market Lead", "BizOps Architect", "Product Strategist", "Partnerships Lead"]
MEDICAL_ROLES = ["Clinical Advisor", "Health Systems Liaison", "Medical Partnerships", "Regulatory Specialist", "Digital Health Strategist"]
OPERATIONS_ROLES = ["Operations Lead", "People Architect", "Finance Strategist", "Customer Success Lead"]

FALLBACK_BIOS = [
    "Former consultant scaling early-stage teams; blends product intuition with revenue experimentation.",
    "Healthcare operator with a track record of launching patient experience pilots across multi-site networks.",
    "Ex-operations lead who redesigned onboarding and improved activation by 38%.",
    "Built partnerships funnel closing Fortune 500 pilots; passionate about category creation.",
    "Regulatory specialist navigating HIPAA, GDPR and clinical integration pathways." 
]

class SyntheticProfileGenerator:
    def __init__(self, max_profiles: int = 5):
        self.max_profiles = max_profiles
        self.client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

    def _base_prompt(self, idea_text: str, domain_hint: str) -> str:
        return f"""
You are generating senior non-technical cofounder persona candidates to complement
a technical founding team. Output STRICT JSON array of objects.
Each object fields: name, role_type, bio, top_strengths (array), strategic_value (string), match_percentage (int 55-95), synergy_analysis (string), recommended_action (string), intro_message (string), source.
Source must be 'synthetic'. role_type must be one of: Business Strategist, Medical Domain Expert, Operations Architect, Growth & Partnerships.
Bias generation toward domain: {domain_hint}. Idea summary: {idea_text}.
Rules:
- Avoid generic filler.
- Provide differentiated strengths.
- intro_message should sound natural and tailored.
- match_percentage distribution: at least one >=85, most between 65-90.
Return ONLY JSON.
""".strip()

    def _fallback(self, idea_text: str, domain_hint: str) -> List[Dict[str, Any]]:
        roles_pool = ["Business Strategist", "Medical Domain Expert", "Operations Architect", "Growth & Partnerships"]
        profiles: List[Dict[str, Any]] = []
        for i in range(min(self.max_profiles, 4)):
            role = roles_pool[i]
            name = random.choice(["Ava Lin", "Rohan Patel", "Maya Brooks", "Elena Ruiz", "Jonah Kim", "Priya Desai"]) + f" {random.choice(['','PhD','MBA'])}".strip()
            bio = random.choice(FALLBACK_BIOS)
            match = random.randint(65, 92)
            profiles.append({
                "name": name,
                "role_type": role,
                "bio": bio,
                "top_strengths": random.sample(["Market Framing","Clinical Workflow","Regulatory Path","Strategic Partnerships","Customer Discovery","Category Narrative","Operational Scaling","Retention Playbooks"], 4),
                "strategic_value": f"Augments technical depth with {role.lower()} leverage.",
                "match_percentage": match,
                "synergy_analysis": f"{role} profile fills non-technical gaps for domain '{domain_hint}'.",
                "recommended_action": "Must Connect" if match >= 85 else ("Strong Option" if match >= 75 else "Explore"),
                "intro_message": f"Hi {name.split()[0]}, exploring {domain_hint} and your background seems highly complementary—open to trading notes?",
                "source": "synthetic"
            })
        return profiles

    def generate(self, idea_text: str, domain_hint: str) -> List[Dict[str, Any]]:
        prompt = self._base_prompt(idea_text, domain_hint)
        if not self.client:
            return self._fallback(idea_text, domain_hint)
        try:
            resp = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1700
            )
            content = resp.choices[0].message.content.strip()
            # Attempt to parse JSON
            data = json.loads(content)
            if isinstance(data, dict):
                # If model returned a dict with key 'profiles'
                data = data.get("profiles", [])
            normalized: List[Dict[str, Any]] = []
            for p in data[:self.max_profiles]:
                normalized.append({
                    "name": p.get("name"),
                    "role_type": p.get("role_type"),
                    "bio": p.get("bio"),
                    "top_strengths": p.get("top_strengths", [])[:6],
                    "strategic_value": p.get("strategic_value"),
                    "match_percentage": int(p.get("match_percentage", 70)),
                    "synergy_analysis": p.get("synergy_analysis") or f"Complements domain {domain_hint} with non-technical leverage.",
                    "recommended_action": p.get("recommended_action", "Explore"),
                    "intro_message": p.get("intro_message", f"Hi, exploring {domain_hint} — your experience looks synergistic; open to a brief chat?"),
                    "source": "synthetic"
                })
            if not normalized:
                return self._fallback(idea_text, domain_hint)
            return normalized
        except Exception:
            return self._fallback(idea_text, domain_hint)

__all__ = ["SyntheticProfileGenerator"]
