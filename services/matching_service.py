"""
Hybrid Semantic Matching Engine for Elevare Platform

This module implements a sophisticated co-founder matching system that combines:
1. Semantic Vector Search (70%): Uses sentence-transformers for bio/vision matching
2. Weighted Jaccard Similarity (30%): For hard skill matching

Architecture:
- SentenceTransformer with 'all-MiniLM-L6-v2' for 384-dimensional embeddings
- Cosine similarity for semantic matching
- Jaccard index for skill set comparison
- Async-ready for non-blocking API integration
"""

from __future__ import annotations

import asyncio
import logging
from functools import lru_cache
from typing import Dict, Iterable, List, Optional, Set, Tuple, Union

import numpy as np
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.user_models import Skill, User

logger = logging.getLogger(__name__)


# =============================================================================
# SINGLETON MODEL LOADER (Performance Optimization)
# =============================================================================

class ModelCache:
    """Singleton cache for the SentenceTransformer model.
    
    Ensures we only load the model once, regardless of how many times
    the matching engine is instantiated.
    """
    _instance: Optional['ModelCache'] = None
    _model: Optional[SentenceTransformer] = None
    _model_name: str = 'all-MiniLM-L6-v2'
    
    def __new__(cls) -> 'ModelCache':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            logger.info(f"🔧 Loading SentenceTransformer model: {self._model_name}")
            self._model = SentenceTransformer(self._model_name)
            logger.info(f"✅ Model loaded successfully: {self._model_name}")
        return self._model


# Global model cache instance
_model_cache = ModelCache()


def get_embedding_model() -> SentenceTransformer:
    """Get the cached SentenceTransformer model."""
    return _model_cache.model


# =============================================================================
# DATA MODELS
# =============================================================================

class MatchScore(BaseModel):
    """Detailed breakdown of a match score."""
    
    user_id: int
    user_name: str
    total_score: float = Field(..., ge=0.0, le=1.0, description="Combined match score (0-1)")
    semantic_score: float = Field(..., ge=0.0, le=1.0, description="Bio/vision similarity (0-1)")
    skill_score: float = Field(..., ge=0.0, le=1.0, description="Skill overlap via Jaccard (0-1)")
    matching_skills: List[str] = Field(default_factory=list, description="Skills in common")
    complementary_skills: List[str] = Field(default_factory=list, description="Skills the other user brings")
    explanation: str = Field(default="", description="Human-readable match explanation")
    
    class Config:
        extra = "forbid"


class ProjectRequirements(BaseModel):
    """Requirements for a project/startup idea."""
    
    description: str = Field(..., description="Project description for semantic matching")
    required_skills: List[str] = Field(default_factory=list, description="Skills needed")
    preferred_interests: List[str] = Field(default_factory=list, description="Preferred interest areas")
    location_preference: Optional[str] = Field(None, description="Optional location filter")


class UserProfile(BaseModel):
    """Simplified user profile for matching."""
    
    id: int
    name: str
    bio: str = ""
    interests: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    past_projects: str = ""
    location: Optional[str] = None
    commitment_level: Optional[float] = None
    personality: Optional[str] = None


# =============================================================================
# HYBRID MATCHING ENGINE
# =============================================================================

class CofounderMatchingEngine:
    """
    Hybrid AI Matching Engine for co-founder discovery.
    
    Combines semantic understanding with skill-based matching:
    - Semantic Signal (70%): Understands context, vision, and passion
    - Skill Signal (30%): Ensures technical/domain competency match
    
    Usage:
        engine = CofounderMatchingEngine(db_session)
        matches = await engine.find_matches(user_id=1, limit=10)
        # or
        matches = await engine.find_matches_for_project(project_reqs, limit=10)
    """
    
    SEMANTIC_WEIGHT = 0.7
    SKILL_WEIGHT = 0.3
    
    def __init__(self, db: Session):
        """
        Initialize the matching engine.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self._model = get_embedding_model()
        self._embedding_cache: Dict[int, np.ndarray] = {}
        logger.debug("CofounderMatchingEngine initialized")
    
    # -------------------------------------------------------------------------
    # EMBEDDING GENERATION
    # -------------------------------------------------------------------------
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate a 384-dimensional embedding vector for the given text.
        
        Args:
            text: Input text to embed (bio, description, etc.)
            
        Returns:
            numpy array of shape (384,) representing the semantic meaning
        """
        if not text or not text.strip():
            # Return zero vector for empty text (neutral in cosine similarity)
            return np.zeros(384)
        
        # Clean and encode
        clean_text = text.strip()
        embedding = self._model.encode(clean_text, convert_to_numpy=True)
        
        # Ensure it's 1D
        if embedding.ndim > 1:
            embedding = embedding.flatten()
        
        return embedding
    
    def _build_user_context(self, user: Union[User, UserProfile]) -> str:
        """
        Build a rich context string for embedding generation.
        
        Combines bio, interests, past projects into a semantic-rich representation.
        """
        parts = []
        
        if isinstance(user, User):
            # SQLAlchemy model
            if hasattr(user, 'bio') and user.bio:
                parts.append(user.bio)
            if user.interest:
                parts.append(f"Interested in {user.interest}")
            if hasattr(user, 'past_projects') and user.past_projects:
                parts.append(f"Worked on {user.past_projects}")
            if user.skills:
                skill_names = [s.name for s in user.skills]
                parts.append(f"Skills: {', '.join(skill_names)}")
        else:
            # Pydantic model
            if user.bio:
                parts.append(user.bio)
            if user.interests:
                parts.append(f"Interested in {', '.join(user.interests)}")
            if user.past_projects:
                parts.append(f"Worked on {user.past_projects}")
            if user.skills:
                parts.append(f"Skills: {', '.join(user.skills)}")
        
        return " ".join(parts) if parts else ""
    
    def _get_user_embedding(self, user: User) -> np.ndarray:
        """Get or compute the embedding for a user (with caching)."""
        if user.id in self._embedding_cache:
            return self._embedding_cache[user.id]
        
        context = self._build_user_context(user)
        embedding = self.generate_embedding(context)
        self._embedding_cache[user.id] = embedding
        
        return embedding
    
    # -------------------------------------------------------------------------
    # SIMILARITY CALCULATIONS
    # -------------------------------------------------------------------------
    
    def calculate_semantic_similarity(
        self,
        embedding_a: np.ndarray,
        embedding_b: np.ndarray
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding_a: First embedding vector
            embedding_b: Second embedding vector
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Handle zero vectors (empty bios)
        if np.allclose(embedding_a, 0) or np.allclose(embedding_b, 0):
            return 0.0
        
        # Reshape for sklearn
        a = embedding_a.reshape(1, -1)
        b = embedding_b.reshape(1, -1)
        
        # Cosine similarity returns [-1, 1], normalize to [0, 1]
        similarity = cosine_similarity(a, b)[0][0]
        normalized = (similarity + 1) / 2
        
        return float(max(0.0, min(1.0, normalized)))
    
    def calculate_jaccard_similarity(
        self,
        skills_a: Set[str],
        skills_b: Set[str]
    ) -> float:
        """
        Calculate Jaccard similarity index between two skill sets.
        
        J(A, B) = |A ∩ B| / |A ∪ B|
        
        Args:
            skills_a: First skill set (normalized to lowercase)
            skills_b: Second skill set (normalized to lowercase)
            
        Returns:
            Jaccard index between 0.0 and 1.0
        """
        if not skills_a and not skills_b:
            return 0.0
        
        # Normalize to lowercase for fair comparison
        a_normalized = {s.lower().strip() for s in skills_a if s}
        b_normalized = {s.lower().strip() for s in skills_b if s}
        
        if not a_normalized and not b_normalized:
            return 0.0
        
        intersection = len(a_normalized & b_normalized)
        union = len(a_normalized | b_normalized)
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def calculate_hybrid_score(
        self,
        user_embedding: np.ndarray,
        user_skills: Set[str],
        target_embedding: np.ndarray,
        target_skills: Set[str]
    ) -> Tuple[float, float, float]:
        """
        Calculate the hybrid matching score.
        
        Formula: Final = (Semantic × 0.7) + (Skill × 0.3)
        
        Args:
            user_embedding: Embedding of the searching user/project
            user_skills: Skills of the searching user/project requirements
            target_embedding: Embedding of the candidate
            target_skills: Skills of the candidate
            
        Returns:
            Tuple of (total_score, semantic_score, skill_score)
        """
        semantic_score = self.calculate_semantic_similarity(
            user_embedding, target_embedding
        )
        
        skill_score = self.calculate_jaccard_similarity(
            user_skills, target_skills
        )
        
        total_score = (
            (self.SEMANTIC_WEIGHT * semantic_score) +
            (self.SKILL_WEIGHT * skill_score)
        )
        
        return (
            round(total_score, 4),
            round(semantic_score, 4),
            round(skill_score, 4)
        )
    
    # -------------------------------------------------------------------------
    # MATCHING METHODS
    # -------------------------------------------------------------------------
    
    async def find_matches(
        self,
        user_id: int,
        limit: int = 20,
        min_score: float = 0.1
    ) -> List[MatchScore]:
        """
        Find the best co-founder matches for a given user.
        
        This is the primary async matching method for user-to-user matching.
        
        Args:
            user_id: ID of the user seeking matches
            limit: Maximum number of matches to return
            min_score: Minimum score threshold (0-1)
            
        Returns:
            List of MatchScore objects sorted by total_score descending
        """
        # Run the blocking DB operations in a thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._find_matches_sync,
            user_id,
            limit,
            min_score
        )
    
    def _find_matches_sync(
        self,
        user_id: int,
        limit: int = 20,
        min_score: float = 0.1
    ) -> List[MatchScore]:
        """Synchronous implementation of find_matches."""
        me = self.db.get(User, user_id)
        if not me:
            logger.warning(f"User {user_id} not found for matching")
            return []
        
        # Build my embedding and skills
        my_embedding = self._get_user_embedding(me)
        my_skills = {s.name.lower() for s in me.skills}
        
        # Get all other users
        candidates = self.db.scalars(
            select(User).where(User.id != user_id)
        ).all()
        
        matches: List[MatchScore] = []
        
        for candidate in candidates:
            candidate_embedding = self._get_user_embedding(candidate)
            candidate_skills = {s.name.lower() for s in candidate.skills}
            
            total, semantic, skill = self.calculate_hybrid_score(
                my_embedding, my_skills,
                candidate_embedding, candidate_skills
            )
            
            if total < min_score:
                continue
            
            # Build match details
            matching = list(my_skills & candidate_skills)
            complementary = list(candidate_skills - my_skills)
            
            explanation = self._generate_explanation(
                candidate.name, total, semantic, skill,
                matching, complementary
            )
            
            matches.append(MatchScore(
                user_id=candidate.id,
                user_name=candidate.name,
                total_score=total,
                semantic_score=semantic,
                skill_score=skill,
                matching_skills=matching,
                complementary_skills=complementary,
                explanation=explanation
            ))
        
        # Sort by total score descending
        matches.sort(key=lambda m: m.total_score, reverse=True)
        
        logger.info(f"Found {len(matches)} matches for user {user_id}, returning top {limit}")
        return matches[:limit]
    
    async def find_matches_for_project(
        self,
        project: ProjectRequirements,
        limit: int = 20,
        min_score: float = 0.1,
        exclude_user_ids: Optional[List[int]] = None
    ) -> List[MatchScore]:
        """
        Find the best co-founders for a project/startup idea.
        
        Args:
            project: Project requirements including description and skills
            limit: Maximum matches to return
            min_score: Minimum score threshold
            exclude_user_ids: User IDs to exclude (e.g., the founder)
            
        Returns:
            List of MatchScore objects sorted by total_score descending
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._find_matches_for_project_sync,
            project,
            limit,
            min_score,
            exclude_user_ids or []
        )
    
    def _find_matches_for_project_sync(
        self,
        project: ProjectRequirements,
        limit: int = 20,
        min_score: float = 0.1,
        exclude_user_ids: Optional[List[int]] = None
    ) -> List[MatchScore]:
        """Synchronous implementation of find_matches_for_project."""
        exclude_user_ids = exclude_user_ids or []
        
        # Build project embedding
        project_context = project.description
        if project.preferred_interests:
            project_context += f" Looking for: {', '.join(project.preferred_interests)}"
        
        project_embedding = self.generate_embedding(project_context)
        project_skills = {s.lower() for s in project.required_skills}
        
        # Get all candidates
        query = select(User)
        if exclude_user_ids:
            query = query.where(User.id.notin_(exclude_user_ids))
        
        candidates = self.db.scalars(query).all()
        matches: List[MatchScore] = []
        
        for candidate in candidates:
            candidate_embedding = self._get_user_embedding(candidate)
            candidate_skills = {s.name.lower() for s in candidate.skills}
            
            total, semantic, skill = self.calculate_hybrid_score(
                project_embedding, project_skills,
                candidate_embedding, candidate_skills
            )
            
            if total < min_score:
                continue
            
            matching = list(project_skills & candidate_skills)
            complementary = list(candidate_skills - project_skills)
            
            explanation = self._generate_explanation(
                candidate.name, total, semantic, skill,
                matching, complementary
            )
            
            matches.append(MatchScore(
                user_id=candidate.id,
                user_name=candidate.name,
                total_score=total,
                semantic_score=semantic,
                skill_score=skill,
                matching_skills=matching,
                complementary_skills=complementary,
                explanation=explanation
            ))
        
        matches.sort(key=lambda m: m.total_score, reverse=True)
        
        logger.info(f"Found {len(matches)} matches for project, returning top {limit}")
        return matches[:limit]
    
    def _generate_explanation(
        self,
        name: str,
        total: float,
        semantic: float,
        skill: float,
        matching: List[str],
        complementary: List[str]
    ) -> str:
        """Generate a human-readable explanation of the match."""
        parts = []
        
        # Overall assessment
        if total >= 0.8:
            parts.append(f"🌟 {name} is an excellent match!")
        elif total >= 0.6:
            parts.append(f"✅ {name} is a strong match.")
        elif total >= 0.4:
            parts.append(f"👍 {name} could be a good fit.")
        else:
            parts.append(f"📊 {name} has some relevant qualities.")
        
        # Semantic insight
        if semantic >= 0.7:
            parts.append("Your visions are highly aligned.")
        elif semantic >= 0.5:
            parts.append("You share similar interests and goals.")
        
        # Skills insight
        if matching:
            parts.append(f"Shared skills: {', '.join(matching[:3])}")
        if complementary:
            parts.append(f"Brings: {', '.join(complementary[:3])}")
        
        return " ".join(parts)
    
    # -------------------------------------------------------------------------
    # LEGACY COMPATIBILITY LAYER
    # -------------------------------------------------------------------------
    
    def get_matches(self, user_id: int, limit: int = 20) -> List[Tuple[User, float]]:
        """
        Legacy synchronous method for backward compatibility.
        
        Returns matches in the old format: List[(User, score)]
        """
        matches = self._find_matches_sync(user_id, limit)
        
        result = []
        for match in matches:
            user = self.db.get(User, match.user_id)
            if user:
                # Convert 0-1 score to 0-100 for legacy compatibility
                legacy_score = match.total_score * 100
                result.append((user, legacy_score))
        
        return result


# =============================================================================
# LEGACY SERVICE WRAPPER (Backward Compatibility)
# =============================================================================

class MatchingService:
    """
    Legacy MatchingService for backward compatibility.
    
    This class wraps the new CofounderMatchingEngine while maintaining
    the original API for existing code that depends on it.
    
    Deprecated: Use CofounderMatchingEngine directly for new code.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._engine = CofounderMatchingEngine(db)
    
    # --- User and Skill CRUD helpers (preserved from original) ---
    
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
        """Create or update a user."""
        existing = self.db.scalar(select(User).where(User.email == email))
        if existing:
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
    
    # --- Matching (delegated to new engine) ---
    
    def get_matches(self, user_id: int, limit: int = 20) -> List[Tuple[User, float]]:
        """
        Get matches using the new hybrid matching engine.
        
        Returns legacy format for backward compatibility.
        """
        return self._engine.get_matches(user_id, limit)
    
    def _score_pair(self, a: User, b: User) -> float:
        """
        Legacy scoring method - now uses hybrid engine internally.
        
        Deprecated: Use CofounderMatchingEngine.calculate_hybrid_score() instead.
        """
        a_embedding = self._engine._get_user_embedding(a)
        b_embedding = self._engine._get_user_embedding(b)
        a_skills = {s.name.lower() for s in a.skills}
        b_skills = {s.name.lower() for s in b.skills}
        
        total, _, _ = self._engine.calculate_hybrid_score(
            a_embedding, a_skills,
            b_embedding, b_skills
        )
        
        # Convert to 0-100 scale for legacy compatibility
        return total * 100


# =============================================================================
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# =============================================================================

def create_matching_engine(db: Session) -> CofounderMatchingEngine:
    """Factory function to create a matching engine instance."""
    return CofounderMatchingEngine(db)


async def find_cofounder_matches(
    db: Session,
    user_id: int,
    limit: int = 20
) -> List[MatchScore]:
    """
    Convenience async function for finding co-founder matches.
    
    Usage:
        matches = await find_cofounder_matches(db, user_id=1, limit=10)
    """
    engine = CofounderMatchingEngine(db)
    return await engine.find_matches(user_id, limit)
