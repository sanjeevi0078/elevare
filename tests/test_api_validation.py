import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
import json

def test_refine_idea_success(client: TestClient, mock_external_apis):
    """
    Test the /refine-idea endpoint with a valid input.
    """
    # Setup mock Groq response
    mock_refined_idea = {
        "idea_title": "Test Startup",
        "problem_statement": "Testing is hard",
        "solution_concept": "Automated testing",
        "target_user": "Developers",
        "core_domain": "SaaS",
        "suggested_location": "US",
        "initial_feasibility_score": 4.5,
        "nlp_suggestions": ["Add more tests"]
    }
    
    # The mock_external_apis fixture returns the mock_groq object
    mock_external_apis.chat.completions.create.return_value.choices[0].message.content = json.dumps(mock_refined_idea)
    
    response = client.post(
        "/refine-idea",
        json={"raw_idea_text": "I want to build a startup that helps developers test their code automatically."}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "refined_idea" in data
    assert "market_profile" in data
    assert "overall_confidence_score" in data
    assert data["refined_idea"]["idea_title"] == "Test Startup"

def test_refine_idea_too_short(client: TestClient):
    """
    Test validation for short input.
    """
    response = client.post(
        "/refine-idea",
        json={"raw_idea_text": "Short"}
    )
    
    assert response.status_code == 422
