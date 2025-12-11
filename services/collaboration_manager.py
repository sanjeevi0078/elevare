"""
Collaboration Manager
Manages WebSocket connections for real-time team collaboration.

This singleton service enables:
1. Real-time team chat and notifications
2. Agent-to-team communication
3. Multi-user collaborative sessions
"""

from fastapi import WebSocket
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Singleton manager for WebSocket connections.
    
    Maintains active connections grouped by team_id, allowing:
    - Real-time broadcasts to team members
    - Agent notifications delivered to users instantly
    - Multi-user collaboration support
    """
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, team_id: str):
        """
        Accept a new WebSocket connection and add it to the team's connection pool.
        
        Args:
            websocket: The WebSocket connection instance
            team_id: Unique identifier for the team/workspace
        """
        await websocket.accept()
        
        if team_id not in self.active_connections:
            self.active_connections[team_id] = []
        
        self.active_connections[team_id].append(websocket)
        logger.info(f"✅ WebSocket connected for team {team_id}. Active connections: {len(self.active_connections[team_id])}")
    
    def disconnect(self, websocket: WebSocket, team_id: str):
        """
        Remove a WebSocket connection from the team's connection pool.
        
        Args:
            websocket: The WebSocket connection to remove
            team_id: The team identifier
        """
        if team_id in self.active_connections:
            try:
                self.active_connections[team_id].remove(websocket)
                logger.info(f"🔌 WebSocket disconnected from team {team_id}. Remaining: {len(self.active_connections[team_id])}")
                
                # Clean up empty team lists
                if not self.active_connections[team_id]:
                    del self.active_connections[team_id]
            except ValueError:
                logger.warning(f"Attempted to disconnect non-existent WebSocket for team {team_id}")
    
    async def broadcast_message(self, message: str, team_id: str):
        """
        Broadcast a message to all connected clients in a specific team.
        
        This is used by:
        - Agents to send notifications (e.g., "Analysis complete!")
        - Team members to send chat messages
        - System to send alerts
        
        Args:
            message: The message text to broadcast
            team_id: The team to broadcast to
        """
        if team_id not in self.active_connections:
            logger.warning(f"No active connections for team {team_id}. Message not sent.")
            return
        
        # Track failed connections for cleanup
        failed_connections = []
        
        for connection in self.active_connections[team_id]:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Failed to send message to connection: {e}")
                failed_connections.append(connection)
        
        # Clean up failed connections
        for failed_conn in failed_connections:
            self.disconnect(failed_conn, team_id)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """
        Send a message to a specific WebSocket connection.
        
        Args:
            message: The message to send
            websocket: The target WebSocket connection
        """
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
    
    def get_team_connection_count(self, team_id: str) -> int:
        """
        Get the number of active connections for a team.
        
        Args:
            team_id: The team identifier
            
        Returns:
            Number of active WebSocket connections
        """
        return len(self.active_connections.get(team_id, []))
    
    def get_all_teams(self) -> List[str]:
        """
        Get a list of all teams with active connections.
        
        Returns:
            List of team IDs with at least one active connection
        """
        return list(self.active_connections.keys())


# Create a single, globally accessible instance
# This singleton pattern ensures all parts of the app share the same connection state
manager = ConnectionManager()

logger.info("✅ Collaboration Manager initialized")
