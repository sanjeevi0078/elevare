"""
Autonomous Agent API
Exposes the multi-agent workflow via FastAPI with streaming support.

This module provides endpoints for:
1. Invoking the autonomous workflow with SSE streaming
2. Getting workflow status
3. Querying available agent capabilities
"""

import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from logger import logger
from exceptions import ElevareException, BusinessLogicError, ExternalServiceError, NotFoundError
from services.agent_workflow import app as workflow_app

# In-memory conversation store to satisfy "View Full Report" modal.
# This is a lightweight buffer for the last run per conversation_id.
CONVERSATIONS: dict[str, dict] = {}

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["Autonomous Agent"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class AgentInvokeRequest(BaseModel):
    """Request model for invoking the autonomous agent workflow."""
    raw_idea: str = Field(
        ...,
        description="The raw, natural language description of the startup idea",
        min_length=10,
        max_length=5000,
        examples=["A mobile app that helps freelancers track time and generate invoices"]
    )
    conversation_id: str = Field(
        default="default",
        description="Unique ID for the user's conversation session (enables memory across invocations)",
        examples=["user-123-session-456", "anonymous-abc123"]
    )
    team_id: str = Field(
        default="default",
        description="Team identifier for real-time collaboration and notifications (Phase 4)",
        examples=["team-123", "user-alice-startup"]
    )
    stream: bool = Field(
        default=True,
        description="Whether to stream results in real-time via SSE"
    )


class AgentStatusResponse(BaseModel):
    """Response model for agent status."""
    status: str
    available_agents: list[str]
    version: str


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/status", response_model=AgentStatusResponse)
async def get_agent_status():
    """
    Get the status and capabilities of the autonomous agent system.
    
    Returns:
        Information about available agents, tools, and system status
    """
    return AgentStatusResponse(
        status="active",
        available_agents=[
            "idea_validation_agent",
            "team_building_agent",
            "market_analysis_agent",
            "recommendation_agent"
        ],
        version="2.0.0-alpha"
    )


@router.post("/invoke")
async def invoke_agent_workflow(request: AgentInvokeRequest):
    """
    Invoke the full autonomous agent workflow.
    
    This endpoint orchestrates multiple specialized agents to provide:
    1. Idea validation and scoring
    2. Team building recommendations
    3. Market analysis
    4. Comprehensive final report
    
    Args:
        request: Contains the raw startup idea and streaming preference
        
    Returns:
        - If stream=True: Server-Sent Events stream with real-time updates
        - If stream=False: Final result after complete workflow execution
    """
    try:
        # Validate input
        if not request.raw_idea or len(request.raw_idea.strip()) < 10:
            raise HTTPException(
                status_code=400,
                detail="Idea description must be at least 10 characters"
            )
        
        # Define initial state (Phase 4: Added team_id for collaboration)
        initial_state = {
            "raw_idea": request.raw_idea,
            "team_id": request.team_id,  # Phase 4: Team collaboration
            "messages": [],
            "validation_profile": {},
            "dimensions": {},  # Module 1: Dimensional scores
            "domain": [],  # Module 1: Domain classification
            "domain_confidence": 0.0,  # Module 1: Domain confidence score
            "overall_score": 0.0,  # Module 1: Overall dimensional score
            "cofounder_matches": [],
            "market_insights": {},
            "funding_report": "",
            "legal_report": "",
            "final_report": "",
            "next_action": "start"
        }
        
        # Phase 3: Configuration for conversation memory
        config = {
            "configurable": {
                "thread_id": request.conversation_id
            }
        }
        
        if request.stream:
            # Stream results in real-time using SSE
            return EventSourceResponse(
                stream_workflow_events(initial_state, config),
                media_type="text/event-stream"
            )
        else:
            # Execute workflow and return final result
            final_state = await execute_workflow(initial_state, config)

            # XAI Debug logging
            logger.info(f"🔍 API Debug - final_state keys: {list(final_state.keys())}")
            logger.info(f"🔍 API Debug - dimension_explanations present: {'dimension_explanations' in final_state}")
            if "dimension_explanations" in final_state:
                expl = final_state.get("dimension_explanations", {})
                logger.info(f"🔍 API Debug - explanation keys: {list(expl.keys())}")
                if expl:
                    sample_key = list(expl.keys())[0]
                    logger.info(f"🔍 API Debug - Sample ({sample_key}): {expl[sample_key][:100]}")

            # Normalize and store conversation history for later retrieval
            msgs = []
            for m in final_state.get("messages", []):
                try:
                    role = getattr(m, "type", None) or ("ai" if m.__class__.__name__.startswith("AI") else "user")
                    content = getattr(m, "content", "")
                    msgs.append({"role": role, "content": content})
                except Exception:
                    pass
            CONVERSATIONS[request.conversation_id] = {"messages": msgs}

            return {
                "status": "completed",
                "conversation_id": request.conversation_id,
                "final_report": final_state.get("final_report", ""),
                "validation_profile": final_state.get("validation_profile", {}),
                "dimensions": final_state.get("dimensions", {}),  # Module 1
                "dimension_explanations": final_state.get("dimension_explanations", {}),  # XAI Module
                "domain": final_state.get("domain", []),  # Module 1
                "domain_confidence": final_state.get("domain_confidence", 0.0),  # Module 1
                "overall_score": final_state.get("overall_score", 0.0),  # Module 1
                "cofounder_matches": final_state.get("cofounder_matches", []),
                "funding_report": final_state.get("funding_report", ""),
                "legal_report": final_state.get("legal_report", "")
            }
            
    except Exception as e:
        logger.exception("Error invoking agent workflow")
        raise HTTPException(
            status_code=500,
            detail=f"Workflow execution failed: {str(e)}"
        )


@router.get("/invoke/stream")
async def invoke_agent_workflow_stream(raw_idea: str, conversation_id: str = "default", team_id: str = "default"):
    """Browser-friendly SSE endpoint for EventSource (GET only).

    Query params mirror AgentInvokeRequest. This avoids the limitation that
    EventSource cannot POST.
    """
    try:
        if not raw_idea or len(raw_idea.strip()) < 10:
            raise BusinessLogicError(message="Idea description must be at least 10 characters")

        initial_state = {
            "raw_idea": raw_idea,
            "team_id": team_id,
            "messages": [],
            "validation_profile": {},
            "dimensions": {},
            "domain": [],
            "domain_confidence": 0.0,
            "overall_score": 0.0,
            "cofounder_matches": [],
            "market_insights": {},
            "funding_report": "",
            "legal_report": "",
            "final_report": "",
            "next_action": "start"
        }

        config = {"configurable": {"thread_id": conversation_id}}

        return EventSourceResponse(
            stream_workflow_events(initial_state, config),
            media_type="text/event-stream"
        )
    except ElevareException:
        raise
    except Exception as e:
        logger.error(f"Error invoking agent workflow (GET stream): {e}", exc_info=True)
        raise ExternalServiceError(service_name="Agent Workflow", message="Workflow execution failed", original_error=e)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def stream_workflow_events(initial_state: dict, config: dict) -> AsyncGenerator[dict, None]:
    """
    Stream workflow execution events in real-time.
    
    This generator yields Server-Sent Events as the workflow progresses
    through different nodes and tool calls.
    
    Args:
        initial_state: The initial state for the workflow
        config: Configuration including conversation_id for memory
        
    Yields:
        SSE-formatted events with workflow progress updates
    """
    try:
        # Send start event
        yield {
            "event": "workflow_started",
            "data": json.dumps({
                "status": "started",
                "conversation_id": config["configurable"]["thread_id"],
                "idea": initial_state["raw_idea"][:100] + "..."
            })
        }
        
        # Stream events from the workflow (Phase 3: Pass config for memory)
        async for event in workflow_app.astream_events(initial_state, config=config, version="v1"):
            event_type = event.get("event", "unknown")
            event_data = event.get("data", {})
            
            # Filter and format events for the client
            if event_type in ["on_chain_start", "on_chain_end", "on_tool_start", "on_tool_end"]:
                yield {
                    "event": event_type,
                    "data": json.dumps({
                        "type": event_type,
                        "name": event.get("name", ""),
                        "data": str(event_data)[:500]  # Limit data size
                    })
                }
        
        # Send completion event
        yield {
            "event": "workflow_completed",
            "data": json.dumps({"status": "completed"})
        }
        
    except Exception as e:
        logger.exception("Error streaming workflow events")
        yield {
            "event": "error",
            "data": json.dumps({"error": str(e)})
        }


async def execute_workflow(initial_state: dict, config: dict) -> dict:
    """
    Execute the workflow without streaming and return the final state.
    
    Args:
        initial_state: The initial state for the workflow
        config: Configuration including conversation_id for memory
        
    Returns:
        The final state after workflow completion
    """
    try:
        # Use ainvoke for simpler non-streaming execution
        # This will run the entire workflow and return the final state
        final_state = await workflow_app.ainvoke(initial_state, config=config)
        
        return final_state
        
    except Exception as e:
        logger.exception("Error executing workflow")
        raise


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Return the last-run conversation history for the provided ID.

    This supports the intake page's "View Full Report" without requiring
    the checkpointer in LangGraph.
    """
    payload = CONVERSATIONS.get(conversation_id, {"messages": []})
    return payload


@router.post("/invoke-simple")
async def invoke_simple(request: AgentInvokeRequest):
    """
    Simplified endpoint that returns just the final report.
    
    This is a convenience endpoint for clients that only need the final
    recommendation without intermediate steps.
    
    Args:
        request: Contains the raw startup idea
        
    Returns:
        JSON with the final startup readiness report
    """
    try:
        initial_state = {
            "raw_idea": request.raw_idea,
            "messages": [],
            "validation_profile": {},
            "cofounder_matches": [],
            "market_insights": {},
            "final_report": "",
            "next_action": "start"
        }
        
        final_state = await execute_workflow(initial_state)
        
        return {
            "idea": request.raw_idea,
            "report": final_state.get("final_report", "Analysis in progress..."),
            "readiness_score": "Calculating...",  # TODO: Extract from report
            "next_steps": []  # TODO: Parse from report
        }
        
    except Exception as e:
        logger.error(f"Error in simple invoke: {e}", exc_info=True)
        raise ExternalServiceError(service_name="Agent Workflow", message="Analysis failed", original_error=e)
