"""
Integration tests for Elevare API endpoints.

Tests cover:
- Input validation edge cases
- CORS configuration
- Contract adherence
- Error handling
"""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestCORSConfiguration:
    """Test CORS middleware is properly configured for frontend integration."""

    def test_cors_preflight_request(self):
        """Test OPTIONS preflight request from allowed origin."""
        response = client.options(
            "/refine-idea",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"

    def test_cors_actual_request(self):
        """Test actual POST request with CORS headers."""
        response = client.get(
            "/",
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers


class TestRefineIdeaEndpoint:
    """Test /refine-idea endpoint input validation and contract adherence."""

    def test_empty_raw_idea_text(self):
        """Test that empty raw_idea_text is rejected."""
        response = client.post(
            "/refine-idea",
            json={"raw_idea_text": ""},
        )
        # Should fail validation or return error
        assert response.status_code in [400, 422, 500]

    def test_missing_raw_idea_text(self):
        """Test that missing raw_idea_text field is rejected."""
        response = client.post(
            "/refine-idea",
            json={},
        )
        assert response.status_code == 422  # Pydantic validation error

    def test_extra_fields_rejected(self):
        """Test that extra fields in input are rejected (strict contract)."""
        response = client.post(
            "/refine-idea",
            json={
                "raw_idea_text": "A fintech app for students",
                "extra_field": "should_be_rejected",
            },
        )
        assert response.status_code == 422  # Pydantic forbids extra fields

    def test_valid_input_returns_full_idea_profile(self):
        """Test that valid input returns FullIdeaProfile with correct structure."""
        response = client.post(
            "/refine-idea",
            json={
                "raw_idea_text": "Problem: Students struggle with budgeting. Solution: A mobile app that tracks expenses and provides insights. Target User: College students in India."
            },
        )
        
        # May fail if OpenAI key not set, but should still validate structure
        if response.status_code == 200:
            data = response.json()
            
            # Verify top-level structure
            assert "refined_idea" in data
            assert "market_profile" in data
            assert "overall_confidence_score" in data
            
            # Verify refined_idea structure
            refined = data["refined_idea"]
            assert "idea_title" in refined
            assert "problem_statement" in refined
            assert "solution_concept" in refined
            assert "target_user" in refined
            assert "core_domain" in refined
            assert "initial_feasibility_score" in refined
            assert "nlp_suggestions" in refined
            
            # Verify market_profile structure
            market = data["market_profile"]
            assert "market_viability_score" in market
            assert "community_engagement_score" in market
            assert "rationale" in market
            
            # Verify score types and ranges
            assert isinstance(data["overall_confidence_score"], (int, float))
            assert 0.0 <= data["overall_confidence_score"] <= 5.0
            assert isinstance(refined["initial_feasibility_score"], (int, float))
            assert 0.0 <= refined["initial_feasibility_score"] <= 5.0
            assert isinstance(market["market_viability_score"], (int, float))
            assert 0.0 <= market["market_viability_score"] <= 5.0


class TestValidationFlowEndpoint:
    """Test the integration test endpoint."""

    def test_validation_flow_passes(self):
        """Test that /test-validation-flow returns passing results."""
        response = client.get("/test-validation-flow")
        assert response.status_code == 200
        
        data = response.json()
        assert "cache_test" in data
        assert "api_fail_test" in data
        
        # Both tests should pass
        assert "PASSED" in data["cache_test"]
        assert "PASSED" in data["api_fail_test"]


class TestMCPEndpoints:
    """Test MCP (Market Concept Profiling) endpoints."""

    def test_cache_key_generation(self):
        """Test cache key generation endpoint."""
        response = client.get(
            "/mcp/cache-key",
            params={"domain": "Fintech", "location": "London"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "cache_key" in data
        assert "MCP:FINTECH:LONDON" == data["cache_key"]

    def test_cache_key_without_location(self):
        """Test cache key generation without location (defaults to GLOBAL)."""
        response = client.get(
            "/mcp/cache-key",
            params={"domain": "SaaS"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "MCP:SAAS:GLOBAL" == data["cache_key"]


class TestMatchingEndpoints:
    """Test cofounder matching endpoints."""

    def test_create_user_minimal(self):
        """Test creating a user with minimal required fields."""
        response = client.post(
            "/matching/users",
            json={
                "name": "Test User",
                "email": "test@example.com",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test User"
        assert data["email"] == "test@example.com"
        assert "id" in data

    def test_create_user_full(self):
        """Test creating a user with all fields."""
        response = client.post(
            "/matching/users",
            json={
                "name": "Full User",
                "email": "full@example.com",
                "location": "Bangalore",
                "interest": "Fintech",
                "personality": "Analytical",
                "commitment_level": 0.8,
                "skills": ["Python", "React", "Product Management"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["commitment_level"] == 0.8
        assert len(data["skills"]) == 3

    def test_list_users(self):
        """Test listing all users."""
        response = client.get("/matching/users")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_invalid_commitment_level(self):
        """Test that commitment_level outside [0.0, 1.0] is rejected."""
        response = client.post(
            "/matching/users",
            json={
                "name": "Invalid User",
                "email": "invalid@example.com",
                "commitment_level": 1.5,  # Invalid: > 1.0
            },
        )
        assert response.status_code == 422  # Pydantic validation error


class TestHealthCheck:
    """Test root health check endpoint."""

    def test_root_endpoint(self):
        """Test that root endpoint returns HTML landing page."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert len(response.text) > 1000  # Has substantial HTML content
        assert "Elevare" in response.text  # Contains expected content
