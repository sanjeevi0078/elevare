from typing import List, Optional, Literal

from pydantic import BaseModel, Field


DomainLiteral = Literal[
    "Fintech",
    "HealthTech",
    "EdTech",
    "SaaS",
    "E-commerce",
    "ClimateTech",
    "Other",
]


class RawIdeaInput(BaseModel):
    """Input payload capturing the user's raw, natural-language idea."""

    raw_idea_text: str = Field(..., description="The user's natural language idea text.")

    # Forbid extra fields to enforce a strict contract from upstream clients
    model_config = {"extra": "forbid"}


class RefinedIdea(BaseModel):
    """Strict JSON structure expected from the upstream LLM for a refined idea.

    All fields are required unless explicitly noted (suggested_location is optional).
    Extra fields are forbidden to ensure the contract is stable.
    """

    idea_title: str = Field(
        ..., max_length=120, description="A concise, generated name for the startup concept."
    )

    problem_statement: str = Field(..., description="The core pain point being solved.")

    solution_concept: str = Field(..., description="The high-level product or service.")

    target_user: str = Field(..., description="The primary user segment.")

    core_domain: DomainLiteral = Field(
        ...,
        description=(
            "Industry/vertical; one of: 'Fintech', 'HealthTech', 'EdTech', 'SaaS', "
            "'E-commerce', 'ClimateTech', 'Other'."
        ),
    )

    suggested_location: Optional[str] = Field(
        default=None,
        description=(
            "Primary target geographic market or city. Use None if the location is not "
            "clear from the input or LLM output."
        ),
    )

    nlp_suggestions: List[str] = Field(
        ..., description="Suggested enhancements for clarity or niche-narrowing."
    )

    initial_feasibility_score: float = Field(
        ..., ge=0.0, le=5.0, description="Initial LLM-generated technical feasibility score (0.0–5.0)."
    )

    # Enforce strict schema: forbid extra keys coming from the LLM or upstream
    model_config = {"extra": "forbid"}


class MarketViabilityProfile(BaseModel):
    """Structured market viability profile produced by the MCP Service."""

    idea_title: str = Field(..., description="The idea title from the RefinedIdea input.")
    core_domain: DomainLiteral = Field(..., description="Industry vertical for the profile.")
    suggested_location: Optional[str] = Field(
        default=None, description="Primary target geographic market/city (or None)."
    )

    market_viability_score: float = Field(
        ..., ge=0.0, le=5.0, description="Calculated market viability score (0.0–5.0)."
    )

    community_engagement_score: float = Field(
        default=0.0, ge=0.0, le=5.0, description="Default community engagement score for the MVP."
    )

    rationale: str = Field(..., description="Human-readable explanation for the score and key drivers.")

    # Back-compat field used by some clients/tests; mirrors `rationale` when provided.
    # Optional so existing payloads without this field still validate.
    viability_rationale: Optional[str] = Field(
        default=None,
        description="Alias/back-compat field for rationale expected by some clients.",
    )

    # Raw data used to compute the score (optional, may be None on failures)
    raw_trend_score: Optional[float] = Field(None, description="Raw trend score from external sources (0.0–1.0).")
    raw_competitor_count: Optional[int] = Field(None, description="Raw competitor count from external sources.")

    # Optional enterprise fields
    funding_potential_score: Optional[float] = Field(
        default=None, ge=0.0, le=5.0, description="Estimated funding potential (0.0–5.0) based on domain, feasibility, and market."
    )
    funding_rationale: Optional[str] = Field(
        default=None, description="Explanation of the funding potential score including stage/domain factors."
    )
    market_size_bucket: Optional[str] = Field(
        default=None, description="Qualitative market size bucket (niche/moderate/large/very large)."
    )
    market_size_explanation: Optional[str] = Field(
        default=None, description="Rationale for market size based on trend and competition heuristics."
    )

    model_config = {"extra": "forbid"}


__all__ = ["RawIdeaInput", "RefinedIdea", "MarketViabilityProfile"]


class IdeaSearchQueries(BaseModel):
    """Optimized search queries for external APIs derived from idea structure."""
    
    github: str = Field(..., description="GitHub topic/language search query (e.g., 'topic:healthcare-ai language:python')")
    events: str = Field(..., description="Event/conference search query (e.g., 'Health Tech Summit India')")


class IdeaStructure(BaseModel):
    """Structural Blueprint of an idea - the 'crystallized' form that drives intelligent searches.
    
    This structure converts raw idea text into specific, actionable attributes that
    power accurate GitHub developer matching and relevant event discovery.
    """
    
    refined_title: str = Field(
        ..., 
        max_length=100,
        description="Professional 5-7 word name for the concept (e.g., 'AI Clinical Diagnostic Workflow Engine')"
    )
    
    core_domain: str = Field(
        ...,
        description="Broad industry category (e.g., 'Healthcare', 'Finance', 'Education', 'E-commerce')"
    )
    
    target_vertical: str = Field(
        ...,
        description="Specific niche within the domain (e.g., 'Clinical Operations', 'Telemedicine', 'Personal Finance')"
    )
    
    tech_stack: List[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Top 3-5 specific technologies required (e.g., ['Python', 'PyTorch', 'HL7/FHIR', 'React'])"
    )
    
    regulatory_needs: List[str] = Field(
        default_factory=list,
        description="Legal/compliance requirements (e.g., ['HIPAA Compliance', 'GDPR', 'PCI-DSS']) or empty if none"
    )
    
    co_founder_roles: List[str] = Field(
        ...,
        min_length=1,
        max_length=3,
        description="2-3 most critical roles needed to build this (e.g., ['Clinical Lead (MD)', 'Deep Learning Engineer'])"
    )
    
    search_queries: IdeaSearchQueries = Field(
        ...,
        description="Optimized queries for GitHub and Events APIs"
    )
    
    model_config = {"extra": "forbid"}


class FullIdeaProfile(BaseModel):
    """Complete idea profile combining NLP refinement and MCP market profile."""

    refined_idea: RefinedIdea = Field(..., description="The refined idea produced by the NLP module.")
    market_profile: MarketViabilityProfile = Field(..., description="Market viability profile produced by the MCP service.")
    overall_confidence_score: float = Field(..., ge=0.0, le=5.0, description="Combined confidence score (0.0–5.0).")

    # Optional explainability payload for enterprise users
    explainability: Optional[dict] = Field(
        default=None,
        description="Explainable AI payload with human-readable reasons for key scores (feasibility, market, funding)."
    )

    # Optional investor-ready Startup Concept Card (12 sections)
    concept_card: Optional[dict] = Field(
        default=None,
        description=(
            "Structured 'Startup Concept Card' with 12 sections: title, one_line, problem_summary, why_now, "
            "solution_overview, key_features, target_users, user_journey, value_proposition, differentiation, "
            "business_model, future_expansion."
        ),
    )

    model_config = {"extra": "forbid"}


__all__ = ["RawIdeaInput", "RefinedIdea", "MarketViabilityProfile", "FullIdeaProfile", "IdeaStructure", "IdeaSearchQueries"]
