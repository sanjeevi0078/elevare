import pytest
import os
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set testing environment variables
os.environ["TESTING"] = "True"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://mock:6379/0"
os.environ["GROQ_API_KEY"] = "mock_groq_key"
os.environ["GITHUB_TOKEN"] = "mock_github_token"
os.environ["SERPAPI_API_KEY"] = "mock_serp_key"
os.environ["USE_SIMPLE_PARSE_FIRST"] = "false"

# Import app and db after setting env vars
from db.database import Base, get_db
# Ensure models are registered with Base.metadata
import models.user_models

# Create in-memory database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """
    Creates a fresh database session for a test.
    """
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def mock_redis(mocker):
    """
    Mocks the Redis client.
    """
    mock = MagicMock()
    mock.ping.return_value = True
    
    # Mock redis.from_url in various places
    mocker.patch("redis.from_url", return_value=mock)
    mocker.patch("services.mcp_service.get_redis_client", return_value=mock)
    
    return mock

@pytest.fixture(scope="function")
def mock_external_apis(mocker):
    """
    Mocks external APIs (Groq, GitHub, SerpApi).
    """
    # Mock Groq
    mock_groq = MagicMock()
    mock_groq.chat.completions.create.return_value.choices[0].message.content = '{"mock": "response"}'
    mocker.patch("groq.Groq", return_value=mock_groq)
    
    # Patch the global groq_client in api.validation if it exists
    mocker.patch("api.validation.groq_client", mock_groq)
    
    # Mock GitHub
    mocker.patch("httpx.AsyncClient.get", return_value=MagicMock(status_code=200, json=lambda: {}))
    
    return mock_groq

@pytest.fixture(scope="function")
def client(db_session, mock_redis, mock_external_apis):
    """
    FastAPI TestClient with DB override.
    """
    from main import create_application
    app = create_application()
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as c:
        yield c
