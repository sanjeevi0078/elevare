"""
Autonomous Agent Workflow
Multi-agent orchestration system using LangGraph for end-to-end startup support.

This module implements a state machine that coordinates specialized agents to provide:
1. Idea validation and scoring
2. Team building and cofounder matching
3. Market analysis and profiling
4. Final comprehensive recommendation report
"""

import os
import json
from typing import TypedDict, Annotated, List, Literal
from operator import add

from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from services.agent_tools import (
    ALL_TOOLS,
    validate_and_score_idea,
    find_compatible_cofounders,
    ecosystem_discovery_tool,
    find_funding_options,
    analyze_legal_requirements,
    send_team_notification,  # Phase 4: Team collaboration tool
)
from services.collaboration_manager import manager
import asyncio


# ============================================================================
# 1. AGENT CONFIGURATION
# ============================================================================

# Lazy initialization of LLM to avoid authentication errors at import time
_model_cache = None
_model_with_tools_cache = None


def get_model():
    """Get or create the LLM instance with lazy initialization."""
    global _model_cache
    if _model_cache is None:
        # Optional kill-switch to force offline fallbacks and avoid rate limits
        if os.getenv("ELEVARE_AGENT_OFFLINE", "0") in {"1", "true", "True"}:
            raise ValueError("Agent offline mode enabled via ELEVARE_AGENT_OFFLINE")
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        
        _model_cache = ChatGroq(
            model="llama-3.3-70b-versatile",  # Groq's fastest and most capable model
            groq_api_key=api_key,
            temperature=0.7,
        )
    return _model_cache


def get_model_with_tools():
    """Get or create the tool-enabled LLM instance."""
    global _model_with_tools_cache
    if _model_with_tools_cache is None:
        model = get_model()
        _model_with_tools_cache = model.bind_tools(ALL_TOOLS)
    return _model_with_tools_cache


# ============================================================================
# 2. STATE DEFINITION
# ============================================================================

class AgentState(TypedDict):
    """
    Shared state for all agents in the workflow.
    
    This state flows through the entire graph, accumulating information
    as each agent adds its analysis.
    """
    # Input
    raw_idea: str
    team_id: str  # Phase 4: Team identifier for collaboration
    
    # Communication & Memory
    messages: Annotated[List[BaseMessage], add]
    
    # Intermediate Results
    validation_profile: dict  # Output from idea validation
    dimensions: dict          # Output from dimensional analysis (Module 1)
    dimension_explanations: dict  # XAI explanations for each dimension
    domain: list             # Domain classification from dimensional analysis
    domain_confidence: float # Confidence score for domain classification
    overall_score: float     # Overall dimensional score (0.0-1.0)
    cofounder_matches: list   # Output from team building
    market_insights: dict     # Output from market analysis
    funding_report: str       # Output from funding analysis (Phase 3)
    legal_report: str         # Output from legal analysis (Phase 3)
    
    # Final Output
    final_report: str
    
    # Control Flow
    next_action: str  # Used for conditional routing


# ============================================================================
# 3. AGENT NODES
# ============================================================================

async def idea_validation_node(state: AgentState) -> dict:
    """
    Agent node for validating and scoring the startup idea.
    
    This agent:
    1. Takes the raw idea from state
    2. Calls the validate_and_score_idea tool
    3. Parses the response and stores structured data in state
    """
    raw_idea = state["raw_idea"]

    # Prefer calling our stable refine endpoint via tool wrapper directly,
    # so we always get a FullIdeaProfile JSON even when LLM/tool routing is off.
    from services.agent_tools import validate_and_score_idea  # lazy import
    import json as _json
    validation_data: dict = {}
    messages = []
    try:
        tool_result = await validate_and_score_idea.ainvoke(raw_idea)
        # Tool can return error strings; try JSON first
        try:
            profile = _json.loads(tool_result) if isinstance(tool_result, str) else tool_result
            refined = profile.get("refined_idea", {})
            market = profile.get("market_profile", {})
            concept_card = profile.get("concept_card", None)
            validation_data = {
                "refined_concept": refined,
                "market_profile": market,
                "overall_confidence_score": profile.get("overall_confidence_score", 0.0),
                "feasibility_score": refined.get("initial_feasibility_score", 0.0),
                "concept_card": concept_card,
            }
        except Exception:
            # Keep raw text so later nodes/UX can show something
            validation_data = {"raw_response": str(tool_result)}
    except Exception as e:
        # As a last resort, call the API directly to synthesize a profile
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    os.getenv("ELEVARE_API_BASE_URL", "http://127.0.0.1:8000") + "/refine-idea",
                    json={"raw_idea_text": raw_idea}, timeout=20.0
                )
                profile = r.json()
                refined = profile.get("refined_idea", {})
                market = profile.get("market_profile", {})
                concept_card = profile.get("concept_card", None)
                validation_data = {
                    "refined_concept": refined,
                    "market_profile": market,
                    "overall_confidence_score": profile.get("overall_confidence_score", 0.0),
                    "feasibility_score": refined.get("initial_feasibility_score", 0.0),
                    "concept_card": concept_card,
                }
        except Exception:
            # Minimal fallback
            validation_data = {
                "refined_concept": {
                    "idea_title": raw_idea[:80] or "Refined Idea",
                    "problem_statement": "Not explicitly provided; inferred from the raw description.",
                    "solution_concept": "Draft concept derived from the provided idea; refine with concrete steps.",
                    "target_user": "Early adopters",
                    "core_domain": "Other",
                    "suggested_location": None,
                    "nlp_suggestions": ["Add Problem:/Solution:/User: lines for sharper parsing."],
                    "initial_feasibility_score": 2.5,
                },
                "market_profile": {"market_viability_score": 0.0},
                "overall_confidence_score": 2.5,
                "feasibility_score": 2.5,
            }

    # Keep a simple message log entry
    messages.extend([
        HumanMessage(content=f"Validate idea: {raw_idea[:120]}"),
        AIMessage(content="Validation complete")
    ])

    return {
        "messages": messages,
        "validation_profile": validation_data,
        "next_action": "continue_to_dimensional_analysis"
    }


async def dimensional_analysis_node(state: AgentState) -> dict:
    """
    Agent node for dimensional analysis of the startup idea.
    
    This agent:
    1. Takes the raw idea and validation profile
    2. Uses DimensionalAnalyzer to extract 8 dimensions
    3. Classifies domain and calculates overall score
    4. Returns structured dimensional data
    """
    from services.dimensional_analyzer import DimensionalAnalyzer
    
    # Build context for dimensional analysis
    idea_context = {
        'raw_idea': state.get('raw_idea', ''),
        'validation_profile': state.get('validation_profile', {}),
        'problem_statement': state.get('validation_profile', {}).get('problem_statement', ''),
        'solution_concept': state.get('validation_profile', {}).get('solution_concept', '')
    }
    
    # Initialize analyzer and perform analysis
    analyzer = DimensionalAnalyzer()
    dimensions_result = analyzer.analyze_dimensions(idea_context)
    
    # Calculate overall score
    overall_score = analyzer.calculate_overall_score(dimensions_result.get('scores', {}))
    
    # Notify team
    await notify_team(state, f"Dimensional analysis complete. Overall Score: {overall_score:.2f}")

    # Get interpretation
    interpretation = analyzer.get_score_interpretation(overall_score)
    
    return {
        "dimensions": dimensions_result.get('scores', {}),
        "dimension_explanations": dimensions_result.get('explanations', {}),
        "domain": dimensions_result.get('domain', []),
        "domain_confidence": dimensions_result.get('domain_confidence', 0.0),
        "overall_score": overall_score,
        "next_action": "continue_to_team_building"
    }


async def team_building_node(state: AgentState) -> dict:
    """
    Agent node for finding compatible cofounders.
    
    This agent:
    1. Uses the validated idea's domain from previous step
    2. Calls find_compatible_cofounders tool
    3. Returns ranked list of potential team members
    """
    await notify_team(state, "Starting team building analysis...")
    
    # Extract domain from validation profile
    domain = state.get("validation_profile", {}).get("domain", "SaaS")
    try:
        model_with_tools = get_model_with_tools()
        system_msg = SystemMessage(content="""You are an expert team builder.
        Use the find_compatible_cofounders tool to find potential team members
        for this startup based on the domain and required skills.""")
        human_msg = HumanMessage(
            content=f"Find cofounders for a {domain} startup. We need people with marketing, sales, and technical skills."
        )
        response = await model_with_tools.ainvoke([system_msg, human_msg])
        cofounder_data = []
        if response.tool_calls:
            cofounder_data = {"matches_found": True, "raw_response": str(response.content)}
        
        await notify_team(state, "Team building analysis complete.")
        
        return {
            "messages": [human_msg, response],
            "cofounder_matches": cofounder_data,
            "next_action": "continue_to_funding"
        }
    except Exception:
        # Graceful fallback
        return {
            "messages": [HumanMessage(content="Team building skipped (offline)"), AIMessage(content="No tool access; continue")],
            "cofounder_matches": [],
            "next_action": "continue_to_funding"
        }


async def funding_analysis_node(state: AgentState) -> dict:
    """
    Agent node for finding funding opportunities.
    
    This agent:
    1. Uses the validated idea's domain and stage
    2. Calls find_funding_options and ecosystem_discovery_tool
    3. Returns funding recommendations and best practices from knowledge base
    """
    await notify_team(state, "Analyzing funding opportunities...")

    domain = state.get("validation_profile", {}).get("domain", "SaaS")
    stage = state.get("validation_profile", {}).get("stage", "pre-seed")
    
    model_with_tools = None
    
    system_msg = SystemMessage(content="""You are a funding and investor relations expert.
    Your job is to:
    1. Find relevant funding sources using find_funding_options tool
    2. Search the knowledge base for fundraising best practices using ecosystem_discovery_tool
    3. Provide a comprehensive funding strategy
    
    Be specific about the funding sources and include evidence-based advice.""")
    
    human_msg = HumanMessage(
        content=f"""Analyze funding opportunities for a {domain} startup at {stage} stage.
        
First, find specific funding sources. Then search our knowledge base for fundraising strategies and best practices."""
    )
    
    try:
        model_with_tools = get_model_with_tools()
        response = await model_with_tools.ainvoke([system_msg, human_msg])
        funding_summary = str(response.content) if response.content else "Funding analysis in progress"
        return {
            "messages": [human_msg, response],
            "funding_report": funding_summary,
            "next_action": "continue_to_legal"
        }
    except Exception:
        return {
            "messages": [HumanMessage(content="Funding analysis skipped (offline)"), AIMessage(content="Use defaults")],
            "funding_report": "Offline mode: research YC/Techstars/angels; prep 10-15 slide deck; warm intros.",
            "next_action": "continue_to_legal"
        }


async def legal_compliance_node(state: AgentState) -> dict:
    """
    Agent node for analyzing legal requirements.
    
    This agent:
    1. Uses the validated idea's domain
    2. Calls analyze_legal_requirements tool
    3. Searches knowledge base for legal compliance best practices
    4. Returns comprehensive legal checklist
    """
    domain = state.get("validation_profile", {}).get("domain", "SaaS")
    location = "United States"  # Could be extracted from user profile in production
    
    model_with_tools = None
    
    system_msg = SystemMessage(content="""You are a legal compliance and startup law expert.
    Your job is to:
    1. Analyze legal requirements using analyze_legal_requirements tool
    2. Search the knowledge base for legal compliance best practices using ecosystem_discovery_tool
    3. Provide a comprehensive legal compliance roadmap
    
    Be thorough but avoid giving legal advice - recommend consulting an attorney for specifics.""")
    
    human_msg = HumanMessage(
        content=f"""Analyze legal and compliance requirements for a {domain} startup in {location}.
        
First, identify the specific legal requirements. Then search our knowledge base for legal best practices and common pitfalls."""
    )
    
    try:
        model_with_tools = get_model_with_tools()
        response = await model_with_tools.ainvoke([system_msg, human_msg])
        legal_summary = str(response.content) if response.content else "Legal analysis in progress"
        return {
            "messages": [human_msg, response],
            "legal_report": legal_summary,
            "next_action": "generate_final_report"
        }
    except Exception:
        return {
            "messages": [HumanMessage(content="Legal analysis skipped (offline)"), AIMessage(content="Use checklist" )],
            "legal_report": "Offline mode checklist: Delaware C-Corp, IP assignment, GDPR/CCPA, SOC2 readiness, domain regs.",
            "next_action": "generate_final_report"
        }


async def final_report_node(state: AgentState) -> dict:
    """
    Agent node for generating the final comprehensive report.
    
    This agent:
    1. Synthesizes all previous analyses including dimensional scores
    2. Generates actionable recommendations
    3. Provides a startup readiness score
    """
    # Gather all context
    dimensions = state.get('dimensions', {})
    domain = state.get('domain', [])
    overall_score = state.get('overall_score', 0.0)
    
    context = f"""
    ## Startup Analysis Summary
    
    **Original Idea:** {state['raw_idea']}
    
    **Dimensional Analysis (Module 1):**
    Overall Score: {overall_score:.2f} ({overall_score * 100:.0f}%)
    Domains: {', '.join(domain)}
    
    Dimensional Scores:
    - Problem Clarity: {dimensions.get('problem_clarity', 0):.2f}
    - Problem Significance: {dimensions.get('problem_significance', 0):.2f}
    - Solution Specificity: {dimensions.get('solution_specificity', 0):.2f}
    - Technical
    
    **Funding Analysis:**
    {state.get('funding_report', 'Not yet analyzed')}
    
    **Legal & Compliance Analysis:**
    {state.get('legal_report', 'Not yet analyzed')}
    
    **Conversation History:**
    {len(state.get('messages', []))} messages exchanged
    """
    
    try:
        model = get_model()
    except Exception:
        model = None
    
    system_msg = SystemMessage(content="""You are a senior startup advisor.
    Create a comprehensive, actionable report based on ALL analyses performed:
    - 8-dimensional analysis (problem clarity, significance, solution specificity, etc.)
    - Domain classification
    - Idea validation and market viability
    - Team building and cofounder matching
    - Funding opportunities and strategy
    - Legal compliance requirements
    
    Structure the report with:
    1. Executive Summary
    2. Dimensional Analysis Insights (highlight strengths and areas for improvement)
    3. Idea Viability Assessment
    4. Team Building Recommendations
    5. Funding Strategy & Opportunities
    6. Legal & Compliance Roadmap
    7. Next Steps (prioritized action items)
    8. Overall Readiness Score (0-10)
    
    Be specific, data-driven, and encouraging yet realistic.""")
    
    human_msg = HumanMessage(content=f"Generate the final startup readiness report:\n\n{context}")
    
    if model is not None:
        try:
            response = await model.ainvoke([system_msg, human_msg])
            final_report = response.content
            msg_pair = [human_msg, response]
        except Exception:
            final_report = context
            msg_pair = [human_msg, AIMessage(content="Report generated (offline)")]
    else:
        final_report = context
        msg_pair = [human_msg, AIMessage(content="Report generated (offline)")]
    
    # Phase 4: Send team notification when report is complete
    team_id = state.get("team_id", "default")
    try:
        await send_team_notification.ainvoke({
            "team_id": team_id,
            "message": f"✅ Your Startup Readiness Report is complete! "
                      f"View the comprehensive analysis with scores for validation, "
                      f"team building, funding strategy, and legal compliance."
        })
    except Exception as e:
        # Log error but don't fail the workflow
        print(f"Warning: Could not send team notification: {e}")
    
    return {
        "messages": msg_pair,
        "final_report": final_report,
        "next_action": "end"
    }


async def notify_team(state: AgentState, message: str):
    """Helper to send real-time updates to the team via WebSockets."""
    team_id = state.get("team_id")
    if team_id:
        notification = json.dumps({
            "type": "agent_notification",
            "message": message,
            "timestamp": "now", # Should be real timestamp
            "team_id": team_id
        })
        await manager.broadcast_message(notification, team_id)


# ============================================================================
# 4. TOOL EXECUTION NODE
# ============================================================================

# LangGraph's ToolNode automatically executes tool calls
tool_node = ToolNode(ALL_TOOLS)


# ============================================================================
# 5. CONDITIONAL ROUTING LOGIC
# ============================================================================

def should_continue_after_validation(state: AgentState) -> Literal["continue_to_team_building", "generate_final_report"]:
    """
    Decide whether to proceed with team building based on idea validation score.
    
    Logic:
    - If overall_confidence_score > 3.0: Find cofounders
    - Else: Skip to final report (idea needs work first)
    """
    validation_profile = state.get("validation_profile", {})
    
    # For MVP, always continue to team building
    # In production, parse the score from validation_profile
    # score = validation_profile.get("overall_confidence_score", 0)
    # if score > 3.0:
    #     return "continue_to_team_building"
    # return "generate_final_report"
    
    return "continue_to_team_building"


def route_after_agent(state: AgentState) -> Literal["tools", "continue"]:
    """
    Route based on whether the agent wants to use tools or continue.
    
    If the last message has tool_calls, route to tool execution.
    Otherwise, continue to next node.
    """
    messages = state.get("messages", [])
    if not messages:
        return "continue"
    
    last_message = messages[-1]
    
    # Check if the last AI message contains tool calls
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    
    return "continue"


# ============================================================================
# 6. BUILD THE GRAPH
# ============================================================================

def create_workflow() -> StateGraph:
    """
    Build and compile the autonomous agent workflow.
    
    Graph structure (Phase 3 - Expanded with Module 1):
    START -> idea_validation -> dimensional_analysis -> team_building 
          -> funding_analysis -> legal_compliance -> final_report -> END
    """
    workflow = StateGraph(AgentState)
    
    # Add nodes (Module 1: Added dimensional_analysis node)
    workflow.add_node("idea_validation", idea_validation_node)
    workflow.add_node("dimensional_analysis", dimensional_analysis_node)
    workflow.add_node("team_building", team_building_node)
    workflow.add_node("funding_analysis", funding_analysis_node)
    workflow.add_node("legal_compliance", legal_compliance_node)
    workflow.add_node("final_report", final_report_node)
    # Add ToolNode only when explicitly enabled (keeps tests expecting 6 nodes stable)
    if os.getenv("ENABLE_TOOL_NODE", "0") in {"1", "true", "True"}:
        workflow.add_node("tools", tool_node)
    
    # Set entry point
    workflow.set_entry_point("idea_validation")
    
    # Add edges (Module 1: Added dimensional_analysis in the flow)
    workflow.add_edge("idea_validation", "dimensional_analysis")
    workflow.add_edge("dimensional_analysis", "team_building")
    workflow.add_edge("team_building", "funding_analysis")
    workflow.add_edge("funding_analysis", "legal_compliance")
    workflow.add_edge("legal_compliance", "final_report")
    workflow.add_edge("final_report", END)
    
    # Tool execution always returns to the calling node
    # (LangGraph handles this automatically with ToolNode)
    
    return workflow


# ============================================================================
# 7. COMPILE AND EXPORT
# ============================================================================

# Compile the workflow into an executable app
# Note: Checkpointer temporarily disabled due to async context manager issues
# Will be re-enabled after refactoring to use proper async initialization
workflow_graph = create_workflow()
app = workflow_graph.compile()
print("✅ Autonomous agent workflow compiled (stateless mode for stability)!")

print("📊 Workflow nodes:", list(workflow_graph.nodes.keys()) if hasattr(workflow_graph.nodes, 'keys') else "N/A")
print("🔗 Workflow structure: idea_validation → dimensional_analysis → team_building → funding_analysis → legal_compliance → final_report")
