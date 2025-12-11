"""
Agent Tools - Bridge Layer
Converts existing FastAPI endpoints into agent-callable tools.

This module provides async tool wrappers around our stabilized API endpoints,
enabling AI agents to use them as part of autonomous workflows.
"""

import os
import httpx
from langchain.tools import tool
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from typing import List

# Phase 4: Import collaboration manager for team notifications
from services.collaboration_manager import manager as ws_manager

# Define the API base URL (override with ELEVARE_API_BASE_URL)
API_BASE_URL = os.getenv("ELEVARE_API_BASE_URL", "http://127.0.0.1:8000")


class IdeaInput(BaseModel):
    """Input schema for idea validation tool."""
    idea_text: str = Field(description="The raw, natural language startup idea.")


class CofounderInput(BaseModel):
    """Input schema for cofounder matching tool."""
    domain: str = Field(description="The primary domain, e.g., 'Fintech' or 'HealthTech'")
    skills_needed: List[str] = Field(description="A list of skills the user is looking for.")


@tool
async def validate_and_score_idea(raw_idea_text: str) -> str:
    """
    Validates, refines, and provides a full market/viability score for a startup idea.
    
    This tool calls the /refine-idea endpoint and returns a comprehensive analysis including:
    - Refined problem statement and solution
    - Feasibility score (0-5)
    - Market viability score (0-5)
    - Overall confidence score (0-5)
    - Actionable suggestions
    
    Args:
        raw_idea_text: The natural language description of the startup idea
        
    Returns:
        JSON string containing the FullIdeaProfile with all scores and analysis
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}/refine-idea",
                json={"raw_idea_text": raw_idea_text},
                timeout=30.0
            )
            response.raise_for_status()  # Raise an exception for 4xx/5xx errors
            return response.text  # Return the full JSON profile
        except httpx.HTTPStatusError as e:
            return f"Error: API call failed with status {e.response.status_code}. Response: {e.response.text}"
        except Exception as e:
            return f"Error: Unexpected error occurred: {str(e)}"


@tool
async def find_compatible_cofounders(domain: str, skills_needed: List[str]) -> str:
    """
    Finds and returns a list of potential cofounders based on domain and required skills.
    
    This tool searches the user database for individuals with matching interests and skills.
    It returns scored matches based on:
    - Skills compatibility
    - Domain/interest alignment
    - Location proximity
    - Personality fit
    - Commitment level
    
    Args:
        domain: The primary domain or interest area (e.g., 'Fintech', 'HealthTech')
        skills_needed: List of skills to look for in potential cofounders
        
    Returns:
        JSON string containing list of matched users with scores
    """
    async with httpx.AsyncClient() as client:
        try:
            # First, get all users
            response = await client.get(
                f"{API_BASE_URL}/matching/users",
                timeout=10.0
            )
            response.raise_for_status()
            
            # TODO: In production, enhance the /matching/users endpoint to accept
            # query parameters for filtering by domain and skills
            # For now, we return the full list and let the agent filter
            users_data = response.json()
            
            # Filter users by domain (interest field) if available
            filtered_users = [
                user for user in users_data
                if user.get("interest", "").lower() == domain.lower()
            ]
            
            # If no domain matches, return all users
            if not filtered_users:
                filtered_users = users_data
            
            return f"Found {len(filtered_users)} potential cofounders in {domain}. Full data: {filtered_users}"
            
        except httpx.HTTPStatusError as e:
            return f"Error: API call failed with status {e.response.status_code}."
        except Exception as e:
            return f"Error: Unexpected error occurred: {str(e)}"


@tool
async def get_market_profile(domain: str, location: str = "GLOBAL") -> str:
    """
    Gets market profiling data for a specific domain and location.
    
    This tool analyzes market trends using Google Trends data and provides:
    - Market interest score (0-100)
    - Trend direction (rising/stable/declining)
    - Competitive landscape
    - Regional insights
    
    Args:
        domain: The domain/industry to analyze (e.g., 'AI SaaS', 'HealthTech')
        location: Geographic location for market data (default: 'GLOBAL')
        
    Returns:
        JSON string with market viability profile
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{API_BASE_URL}/mcp/cache-key",
                params={"domain": domain, "location": location},
                timeout=10.0
            )
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as e:
            return f"Error: Market profiling failed with status {e.response.status_code}."
        except Exception as e:
            return f"Error: Unexpected error occurred: {str(e)}"


@tool
async def ecosystem_discovery_tool(query: str) -> str:
    """
    Searches the startup knowledge base for case studies, best practices,
    funding advice, legal guidance, and go-to-market strategies.
    
    Use this tool to provide evidence-based insights from successful startups
    and industry best practices.
    
    Args:
        query: The question or topic to search for in the knowledge base
        
    Returns:
        Relevant insights and recommendations from the knowledge base
    """
    try:
        # Lazy import to avoid circular dependency and API key requirement
        from services.knowledge_base import create_rag_retriever
        
        # Create RAG chain
        retriever = create_rag_retriever(k=3)
        
        # Format documents helper
        def format_docs(docs):
            return "\n\n".join(f"Source: {doc.metadata.get('source', 'Unknown')}\n{doc.page_content}" for doc in docs)
        
        # Simple RAG prompt
        prompt = ChatPromptTemplate.from_template("""Answer the question based on the following context from our startup knowledge base:

Context:
{context}

Question: {question}

Provide a comprehensive answer with specific recommendations and examples from the context.""")
        
        # Get LLM (lazy init)
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return "Error: GROQ_API_KEY not configured. Cannot use RAG tool."
        
        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            groq_api_key=api_key,
            temperature=0.3
        )
        
        # Build RAG chain
        rag_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )
        
        # Execute query
        result = await rag_chain.ainvoke(query)
        return result
        
    except Exception as e:
        return f"Error: Knowledge base query failed: {str(e)}"


@tool
async def find_funding_options(domain: str, stage: str = "pre-seed") -> str:
    """
    Finds relevant grants, accelerators, angel investors, or VCs for a startup.
    
    This tool provides funding recommendations based on the startup's domain
    and current stage (pre-seed, seed, Series A, etc.).
    
    Args:
        domain: The startup's primary domain (e.g., 'Fintech', 'HealthTech', 'AI/ML')
        stage: The funding stage (default: 'pre-seed')
        
    Returns:
        List of recommended funding sources with descriptions
    """
    # Simulated funding database (in production, would query Crunchbase, AngelList, etc.)
    funding_sources = {
        "pre-seed": {
            "Fintech": ["Stripe Atlas", "Plaid Accelerator", "Barclays Accelerator"],
            "HealthTech": ["Rock Health", "Y Combinator", "Techstars Healthcare"],
            "AI/ML": ["OpenAI Startup Fund", "AI2 Incubator", "Google for Startups AI"],
            "SaaS": ["Y Combinator", "500 Startups", "SaaStr Fund"],
            "default": ["Y Combinator", "Techstars", "Angel investors in your network"]
        },
        "seed": {
            "Fintech": ["Ribbit Capital", "QED Investors", "Nyca Partners"],
            "HealthTech": ["Andreessen Horowitz Bio+Health", "Khosla Ventures", "GV (Google Ventures)"],
            "AI/ML": ["Sequoia Capital", "Greylock Partners", "Kleiner Perkins"],
            "SaaS": ["Accel", "Index Ventures", "Bessemer Venture Partners"],
            "default": ["Local VCs", "Seed funds", "Strategic angels"]
        }
    }
    
    stage_lower = stage.lower()
    stage_data = funding_sources.get(stage_lower, funding_sources["pre-seed"])
    sources = stage_data.get(domain, stage_data.get("default", []))
    
    result = f"**Funding Options for {domain} Startup ({stage} stage)**:\n\n"
    
    if sources:
        for i, source in enumerate(sources, 1):
            result += f"{i}. {source}\n"
        
        result += f"\n**Next Steps:**\n"
        result += f"- Research each fund's investment thesis and portfolio\n"
        result += f"- Prepare a compelling deck (10-15 slides)\n"
        result += f"- Warm introductions are 10x more effective than cold emails\n"
        result += f"- Typical {stage} round: "
        
        if stage_lower == "pre-seed":
            result += "$100K-$500K for 5-10% equity"
        elif stage_lower == "seed":
            result += "$1M-$3M for 10-20% equity"
        else:
            result += "varies by stage and market"
    else:
        result += "No specific recommendations found. Consider general startup accelerators and angel networks."
    
    return result


@tool
async def analyze_legal_requirements(domain: str, location: str = "United States") -> str:
    """
    Analyzes common legal requirements and compliance considerations for a startup.
    
    Provides guidance on entity formation, intellectual property, data privacy,
    and industry-specific regulations.
    
    Args:
        domain: The startup's primary domain (e.g., 'Fintech', 'HealthTech')
        location: Primary operating location (default: 'United States')
        
    Returns:
        Legal compliance checklist and recommendations
    """
    result = f"**Legal & Compliance Analysis for {domain} Startup in {location}**:\n\n"
    
    # Entity Formation
    result += "## 1. Entity Formation\n"
    if location == "United States":
        result += "- **Recommended:** Delaware C-Corporation\n"
        result += "  - Investor-friendly, established case law\n"
        result += "  - Required for VC funding\n"
        result += "- **Alternative:** LLC (if bootstrapping or consulting-focused)\n"
    else:
        result += f"- Consult local business attorney for {location}-specific entity types\n"
        result += "- Consider ease of foreign investment if planning to raise from US VCs\n"
    
    # IP Protection
    result += "\n## 2. Intellectual Property\n"
    result += "- **Trademarks:** Register company name and logo (USPTO)\n"
    result += "- **Patents:** File provisional if novel technology/process\n"
    result += "- **Copyrights:** Automatic, but register for enforcement\n"
    result += "- **Trade Secrets:** Document proprietary processes, use NDAs\n"
    result += "- ⚠️ **CRITICAL:** All team members MUST sign IP assignment agreements\n"
    
    # Domain-Specific Regulations
    result += "\n## 3. Industry-Specific Compliance\n"
    
    if domain == "Fintech":
        result += "- **Money Transmitter License:** Required if handling funds\n"
        result += "- **KYC/AML:** Know Your Customer and Anti-Money Laundering procedures\n"
        result += "- **SEC Regulations:** If dealing with securities\n"
        result += "- **State-by-state licensing:** May be required for lending/payments\n"
    
    elif domain == "HealthTech":
        result += "- **HIPAA Compliance:** If handling Protected Health Information (PHI)\n"
        result += "- **FDA Approval:** Required for medical devices/diagnostics\n"
        result += "- **State Medical Board:** Regulations for telemedicine\n"
        result += "- **Data Security:** HITRUST certification recommended\n"
    
    elif domain == "AI/ML":
        result += "- **Data Privacy:** GDPR (EU), CCPA (California)\n"
        result += "- **Algorithmic Bias:** Emerging regulations on AI fairness\n"
        result += "- **Model Explainability:** Requirements in regulated industries\n"
        result += "- **IP Ownership:** Clarify ownership of AI-generated content\n"
    
    else:
        result += f"- Research {domain}-specific regulations in your jurisdiction\n"
        result += "- Consider data privacy laws (GDPR, CCPA)\n"
        result += "- Review consumer protection regulations\n"
    
    # Data Privacy (Universal)
    result += "\n## 4. Data Privacy & Security\n"
    result += "- **GDPR:** Required if any EU users (even one)\n"
    result += "  - Explicit consent, data portability, right to deletion\n"
    result += "- **CCPA:** Required for California residents\n"
    result += "  - Disclosure of collection, opt-out, deletion rights\n"
    result += "- **SOC 2 Compliance:** Expected by enterprise customers\n"
    
    # Contracts
    result += "\n## 5. Essential Legal Documents\n"
    result += "1. Founders Agreement (equity splits, vesting, roles)\n"
    result += "2. 83(b) Election (file within 30 days of stock grant!)\n"
    result += "3. Employee Offer Letters + IP Assignment\n"
    result += "4. Terms of Service\n"
    result += "5. Privacy Policy\n"
    result += "6. Contractor Agreements\n"
    
    result += "\n**⚠️ ACTION REQUIRED:**\n"
    result += "- Consult startup attorney (cost: $5K-$15K for basic setup)\n"
    result += "- Use Clerky or Carta for document templates (cheaper alternative)\n"
    result += "- File 83(b) election within 30 days of founder stock issuance\n"
    
    return result


@tool
async def send_team_notification(team_id: str, message: str) -> str:
    """
    Sends a real-time message to all users in a specific team's collaboration chat.
    
    Use this tool to:
    - Announce completed analysis tasks
    - Send alerts about important findings
    - Deliver final reports to the team
    - Notify team members of workflow progress
    
    The message will be broadcast via WebSocket to all connected team members instantly.
    
    Args:
        team_id: The unique identifier for the team (e.g., 'team-123', 'user-alice-session')
        message: The message to send (keep concise, max 500 chars recommended)
        
    Returns:
        Confirmation message or error description
        
    Example:
        await send_team_notification(
            team_id="team-123",
            message="✅ Funding analysis complete! Found 3 accelerators matching your profile."
        )
    """
    try:
        # Validate inputs
        if not team_id or not message:
            return "Error: team_id and message are required"
        
        if len(message) > 1000:
            message = message[:997] + "..."  # Truncate long messages
        
        # Format message with timestamp
        import json
        from datetime import datetime
        
        formatted_message = json.dumps({
            "type": "agent_notification",
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "team_id": team_id
        })
        
        # Broadcast to team via WebSocket
        await ws_manager.broadcast_message(formatted_message, team_id)
        
        return f"✅ Successfully sent notification to team {team_id}"
        
    except Exception as e:
        return f"Error sending team notification: {str(e)}"


# Export all tools as a list for easy registration
ALL_TOOLS = [
    validate_and_score_idea,
    find_compatible_cofounders,
    get_market_profile,
    ecosystem_discovery_tool,
    find_funding_options,
    analyze_legal_requirements,
    send_team_notification,  # Phase 4: New collaboration tool
]
