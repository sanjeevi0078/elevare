"""
AI Mentor API
RAG-powered chatbot for startup guidance and mentorship.

This module provides:
1. Evidence-based answers from the startup knowledge base
2. Direct access to the RAG system
3. Simple Q&A interface for users
"""

import logging
from fastapi import APIRouter
from pydantic import BaseModel, Field
from services.agent_tools import ecosystem_discovery_tool  # Import our RAG tool

from logger import logger
from exceptions import ExternalServiceError

# logger = logging.getLogger(__name__) # Use centralized logger

router = APIRouter(prefix="/mentor", tags=["AI Mentor"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class MentorRequest(BaseModel):
    """Request model for AI Mentor questions."""
    question: str = Field(
        ...,
        description="The question to ask the AI Mentor",
        min_length=5,
        max_length=1000,
        examples=[
            "What are the key strategies for achieving product-market fit?",
            "How should I structure equity for my founding team?",
            "What legal requirements do I need for a HealthTech startup?"
        ]
    )


class MentorResponse(BaseModel):
    """Response model for AI Mentor answers."""
    question: str = Field(description="The original question")
    answer: str = Field(description="Evidence-based answer from the knowledge base")
    sources: str = Field(
        default="Startup knowledge base (5 case studies)",
        description="Information about the sources used"
    )


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/ask", response_model=MentorResponse)
async def ask_ai_mentor(request: MentorRequest):
    """
    Ask the AI Mentor a question about startups, fundraising, legal, team building, etc.
    
    The AI Mentor uses RAG (Retrieval Augmented Generation) to provide evidence-based
    answers from our curated startup knowledge base, which includes:
    - Product-market fit strategies
    - Fundraising best practices
    - Team building and equity allocation
    - Legal compliance requirements
    - Go-to-market strategies
    
    Example:
        POST /api/v1/mentor/ask
        {
            "question": "How do I validate product-market fit for a B2B SaaS product?"
        }
        
    Returns:
        {
            "question": "How do I validate...",
            "answer": "Based on successful B2B SaaS case studies, here are the key steps...",
            "sources": "Startup knowledge base (5 case studies)"
        }
    """
    try:
        logger.info(f"🤖 AI Mentor received question: {request.question[:100]}...")
        
        # Call the RAG tool to get evidence-based answer
        answer = await ecosystem_discovery_tool.ainvoke({"query": request.question})
        
        logger.info(f"✅ AI Mentor generated answer ({len(answer)} chars)")
        
        return MentorResponse(
            question=request.question,
            answer=answer,
            sources="Startup knowledge base (5 case studies: PMF, fundraising, team building, legal, GTM)"
        )
        
    except Exception as e:
        logger.error(f"Error in AI Mentor: {e}", exc_info=True)
        raise ExternalServiceError(service_name="AI Mentor", message="AI Mentor encountered an error", original_error=e)


@router.get("/status")
async def get_mentor_status():
    """
    Get the status of the AI Mentor system.
    
    Returns:
        System status and capabilities
    """
    return {
        "status": "operational",
        "backend": "Groq (Llama 3.3 70B)",
        "embeddings": "HuggingFace (all-MiniLM-L6-v2)",
        "knowledge_base": {
            "documents": 5,
            "topics": [
                "Product-Market Fit",
                "Fundraising Strategies",
                "Team Building",
                "Legal Compliance",
                "Go-to-Market Strategies"
            ]
        },
        "capabilities": [
            "Evidence-based startup guidance",
            "Domain-specific recommendations (Fintech, HealthTech, SaaS, etc.)",
            "Funding strategy advice",
            "Legal compliance checklists",
            "Team building best practices"
        ]
    }


@router.get("/topics")
async def get_available_topics():
    """
    Get a list of topics the AI Mentor can help with.
    
    Returns:
        List of available knowledge domains
    """
    return {
        "topics": [
            {
                "name": "Product-Market Fit",
                "description": "Validation strategies, customer discovery, MVP testing",
                "example_questions": [
                    "How do I know if I've achieved product-market fit?",
                    "What metrics should I track for PMF validation?"
                ]
            },
            {
                "name": "Fundraising",
                "description": "VC pitching, accelerators, angel investors, equity negotiation",
                "example_questions": [
                    "What should I include in my investor deck?",
                    "How much equity should I give up in a seed round?"
                ]
            },
            {
                "name": "Team Building",
                "description": "Co-founder matching, equity splits, hiring strategies",
                "example_questions": [
                    "How should I split equity with my co-founders?",
                    "When should I make my first technical hire?"
                ]
            },
            {
                "name": "Legal & Compliance",
                "description": "Entity formation, IP protection, regulations, contracts",
                "example_questions": [
                    "Should I form a Delaware C-Corp or an LLC?",
                    "What is an 83(b) election and when should I file it?"
                ]
            },
            {
                "name": "Go-to-Market",
                "description": "Launch strategies, growth tactics, customer acquisition",
                "example_questions": [
                    "What's the best GTM strategy for a B2B SaaS product?",
                    "How do I acquire my first 100 customers?"
                ]
            }
        ]
    }
