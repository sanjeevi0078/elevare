import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect
from main import create_application
from services.auth_service import AuthService

app = create_application()

def test_websocket_connection_success():
    client = TestClient(app)
    # Generate a valid token
    token = AuthService.create_access_token(subject="test_user")
    
    with client.websocket_connect(f"/api/v1/collaboration/ws/team/team-123?token={token}") as websocket:
        data = websocket.receive_json()
        assert data["type"] == "system"
        assert data["message"] == "Connected to team team-123"

def test_websocket_connection_no_token():
    client = TestClient(app)
    # Should still connect but log warning (based on current implementation)
    # Or fail if we enforce strict auth. Currently we allow it but log warning.
    with client.websocket_connect("/api/v1/collaboration/ws/team/team-123") as websocket:
        data = websocket.receive_json()
        assert data["type"] == "system"

def test_websocket_connection_invalid_token():
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/api/v1/collaboration/ws/team/team-123?token=invalid_token"):
            pass
    assert exc.value.code == 1008

def test_websocket_messaging():
    client = TestClient(app)
    token = AuthService.create_access_token(subject="test_user")
    
    with client.websocket_connect(f"/api/v1/collaboration/ws/team/team-123?token={token}") as websocket:
        # Receive welcome
        websocket.receive_json()
        # Receive join notification (since we are the only one, maybe not? Logic says yes)
        websocket.receive_json() 
        
        # Send message
        websocket.send_json({"type": "chat", "message": "Hello World"})
        
        # Receive echo
        response = websocket.receive_json()
        assert response["type"] == "chat"
        assert response["message"] == "Hello World"
        assert response["team_id"] == "team-123"
