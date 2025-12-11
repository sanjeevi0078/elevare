# Elevare Enterprise Testing Strategy

## Overview
This document outlines the testing strategy for the Elevare platform to ensure enterprise-grade reliability, security, and performance.

## Testing Pyramid

### 1. Unit Tests (Fast, Isolated)
- **Scope**: Individual functions, classes, and services.
- **Tools**: `pytest`, `pytest-mock`.
- **Coverage Target**: >80%.
- **Key Areas**:
    - `services/`: Business logic (e.g., `MatchingService`, `AuthService`).
    - `models/`: Pydantic validation logic.
    - `utils/`: Helper functions.

### 2. Integration Tests (Slower, Connected)
- **Scope**: API endpoints, Database interactions, External API integrations (mocked).
- **Tools**: `TestClient` (FastAPI), `SQLAlchemy` (Test DB).
- **Key Areas**:
    - `api/`: Endpoint contract validation (Status codes, Schemas).
    - `db/`: Database constraints and relationships.
    - **Mocking**: External APIs (GitHub, Groq, SerpApi) MUST be mocked to avoid costs and flakiness.

### 3. End-to-End (E2E) Tests (Slowest, Real User Flows)
- **Scope**: Critical user journeys.
- **Tools**: `Playwright` (Future Phase).
- **Key Flows**:
    - User Registration -> Login -> Profile Setup.
    - Idea Submission -> Refinement -> Result Display.

## Test Infrastructure

### Fixtures (`tests/conftest.py`)
- `db_session`: Creates a fresh SQLite in-memory database for each test session/function.
- `client`: A `TestClient` instance with the `db_session` override.
- `mock_redis`: Mocks Redis operations.
- `mock_external_apis`: Mocks for GitHub, Groq, etc.

### Configuration
- Tests run in a separate environment (`TESTING=True`).
- Database is reset between tests to ensure isolation.

## Continuous Integration (CI)
- Tests should run on every Pull Request.
- Linting (`ruff` or `flake8`) and Type Checking (`mypy`) should run before tests.

## Execution
Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=. --cov-report=term-missing
```
