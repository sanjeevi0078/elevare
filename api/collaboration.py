"""
Collaboration API
Real-time team collaboration via WebSockets.

This module provides:
1. WebSocket endpoint for team chat
2. Real-time notifications from agents
3. Multi-user collaborative sessions
"""

import json
import logging
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from services.collaboration_manager import manager
from services.auth_service import AuthService
from exceptions import AuthenticationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collaboration", tags=["Real-Time Collaboration"])


# ============================================================================
# WEBSOCKET ENDPOINTS
# ============================================================================

@router.websocket("/ws/team/{team_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    team_id: str,
    token: str = Query(None)
):
    """
    Main WebSocket endpoint for a team's real-time chat and notifications.
    
    This endpoint enables:
    - Real-time team chat between co-founders
    - Agent notifications (e.g., "Funding analysis complete!")
    - System alerts and updates
    
    Usage:
        const ws = new WebSocket('ws://localhost:8000/api/v1/collaboration/ws/team/team-123?token=YOUR_JWT_TOKEN');
        ws.onmessage = (event) => console.log(event.data);
        ws.send('Hello team!');
    
    Args:
        websocket: WebSocket connection instance
        team_id: Unique identifier for the team/workspace
        token: JWT access token for authentication
    """
    # Authenticate connection
    user_id = None
    if token:
        try:
            payload = AuthService.verify_token(token)
            user_id = payload.get("sub")
        except Exception as e:
            logger.warning(f"WebSocket authentication failed: {e}")
            await websocket.close(code=1008) # Policy Violation
            return
    else:
        # For now, allow unauthenticated connections in dev, but log warning
        # In production, this should be strict
        logger.warning(f"WebSocket connection attempt without token for team {team_id}")
        # await websocket.close(code=1008)
        # return

    await manager.connect(websocket, team_id)
    
    # Send welcome message
    welcome_msg = json.dumps({
        "type": "system",
        "message": f"Connected to team {team_id}",
        "timestamp": datetime.utcnow().isoformat(),
        "team_id": team_id
    })
    await manager.send_personal_message(welcome_msg, websocket)
    
    # Notify other team members
    join_notification = json.dumps({
        "type": "user_joined",
        "message": "A team member has joined",
        "timestamp": datetime.utcnow().isoformat(),
        "active_users": manager.get_team_connection_count(team_id)
    })
    await manager.broadcast_message(join_notification, team_id)
    
    try:
        while True:
            # Listen for messages from the user
            data = await websocket.receive_text()
            
            # Parse and format the message
            try:
                message_data = json.loads(data)
                message_type = message_data.get("type", "chat")
                message_content = message_data.get("message", data)
            except json.JSONDecodeError:
                # If not JSON, treat as plain text chat message
                message_type = "chat"
                message_content = data
            
            # Create formatted message
            formatted_message = json.dumps({
                "type": message_type,
                "message": message_content,
                "timestamp": datetime.utcnow().isoformat(),
                "team_id": team_id
            })
            
            # Broadcast to all team members (including sender)
            await manager.broadcast_message(formatted_message, team_id)
            
            logger.info(f"📨 Message broadcast to team {team_id}: {message_content[:50]}...")
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, team_id)
        
        # Notify remaining team members
        leave_notification = json.dumps({
            "type": "user_left",
            "message": "A team member has left the chat",
            "timestamp": datetime.utcnow().isoformat(),
            "active_users": manager.get_team_connection_count(team_id)
        })
        await manager.broadcast_message(leave_notification, team_id)
        
        logger.info(f"🔌 User disconnected from team {team_id}")


# ============================================================================
# HTTP ENDPOINTS (for monitoring)
# ============================================================================

@router.get("/teams")
async def get_active_teams():
    """
    Get a list of all teams with active WebSocket connections.
    
    Returns:
        List of team IDs and their connection counts
    """
    teams = manager.get_all_teams()
    return {
        "active_teams": [
            {
                "team_id": team_id,
                "connections": manager.get_team_connection_count(team_id)
            }
            for team_id in teams
        ],
        "total_teams": len(teams)
    }


@router.get("/team/{team_id}/status")
async def get_team_status(team_id: str):
    """
    Get the connection status for a specific team.
    
    Args:
        team_id: The team identifier
        
    Returns:
        Team connection information
    """
    connection_count = manager.get_team_connection_count(team_id)
    
    return {
        "team_id": team_id,
        "active_connections": connection_count,
        "is_active": connection_count > 0
    }
