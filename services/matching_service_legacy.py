from __future__ import annotations
from typing import Iterable, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select

from models.user_models import User, Skill


class MatchingService:
    """Simple cofounder matching service with complementarity scoring.

    Scoring (0-100):
    - Interest diversity: +25 if interests differ and both set, else +10 if only one set, else +0
    - Skill complementarity: +3 per non-overlapping skill between users (cap +30)
    - Personality heuristic: +15 if personalities differ and both set
    - Commitment alignment: +30 * (1 - abs(a-b)) where a,b in [0,1]; if missing, +10 baseline
    """

    def __init__(self, db: Session):
        self.db = db

    # --- User and Skill CRUD helpers ---
    def create_user(
        self,
        name: str,
        email: str,
        location: Optional[str] = None,
        interest: Optional[str] = None,
        personality: Optional[str] = None,
        commitment_level: Optional[float] = None,
        skills: Optional[Iterable[str]] = None,
    ) -> User:
        # Idempotent create: return existing by unique email if present
        existing = self.db.scalar(select(User).where(User.email == email))
        if existing:
            # Optionally update basic fields if new data provided
            existing.name = name or existing.name
            if location is not None:
                existing.location = location
            if interest is not None:
                existing.interest = interest
            if personality is not None:
                existing.personality = personality
            if commitment_level is not None:
                existing.commitment_level = commitment_level
            if skills:
                # Merge skills, ensuring uniqueness
                new_skills = {s.strip().lower() for s in skills}
                have = {s.name.lower() for s in existing.skills}
                for s in (new_skills - have):
                    existing.skills.append(self._get_or_create_skill(s))
            self.db.commit()
            self.db.refresh(existing)
            return existing

        user = User(
            name=name,
            email=email,
            location=location,
            interest=interest,
            personality=personality,
            commitment_level=commitment_level,
        )
        if skills:
            user.skills = [self._get_or_create_skill(s) for s in set(skills)]
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def list_users(self) -> List[User]:
        return list(self.db.scalars(select(User)).all())
    
    def get_user(self, user_id: int) -> Optional[User]:
        """Get a single user by ID."""
        return self.db.get(User, user_id)

    def _get_or_create_skill(self, name: str) -> Skill:
        name = name.strip()
        skill = self.db.scalar(select(Skill).where(Skill.name == name))
        if skill:
            return skill
        skill = Skill(name=name)
        self.db.add(skill)
        self.db.flush()
        return skill

    # --- Matching ---
    def get_matches(self, user_id: int, limit: int = 20) -> List[Tuple[User, float]]:
        me = self.db.get(User, user_id)
        if not me:
            return []
        candidates = self.db.scalars(select(User).where(User.id != user_id)).all()
        scored: List[Tuple[User, float]] = []
        for other in candidates:
            score = self._score_pair(me, other)
            scored.append((other, score))
        scored.sort(key=lambda t: t[1], reverse=True)
        return scored[:limit]

    def _score_pair(self, a: User, b: User) -> float:
        score = 0.0
        # Interest diversity
        if a.interest and b.interest:
            score += 25.0 if a.interest.strip().lower() != b.interest.strip().lower() else 5.0
        elif a.interest or b.interest:
            score += 10.0
        # Skill complementarity (non-overlap)
        skills_a = {s.name.lower() for s in a.skills}
        skills_b = {s.name.lower() for s in b.skills}
        non_overlap = len((skills_a - skills_b) | (skills_b - skills_a))
        score += min(30.0, non_overlap * 3.0)
        # Personality heuristic
        if a.personality and b.personality and a.personality.strip().lower() != b.personality.strip().lower():
            score += 15.0
        # Commitment alignment
        if a.commitment_level is not None and b.commitment_level is not None:
            # closer commitments => higher score
            score += 30.0 * (1.0 - abs(float(a.commitment_level) - float(b.commitment_level)))
        else:
            score += 10.0
        # Normalize hard cap
        return min(100.0, round(score, 3))
