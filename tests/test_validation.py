import json
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch


def _load_validation_module():
    """Locate and import the `api/validation.py` module from the project.

    This helper is robust: it looks in a few sensible locations relative to the
    repository root so tests can run both when module is a package (e.g.
    `elevare.api.validation`) or a plain `api/validation.py` file.
    """
    import importlib.util

    repo_root = Path(__file__).resolve().parents[1]
    candidates = [
        repo_root / "api" / "validation.py",
        repo_root / "elevare" / "api" / "validation.py",
        repo_root / "src" / "api" / "validation.py",
    ]

    for p in candidates:
        if p.exists():
            spec = importlib.util.spec_from_file_location("api_validation_under_test", str(p))
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            return module

    raise RuntimeError("Could not find api/validation.py - checked: %s" % ", ".join(str(x) for x in candidates))


@pytest.fixture
def test_app():
    mod = _load_validation_module()

    # Build a small FastAPI app that mounts the router or uses the app from the module
    if hasattr(mod, "app"):
        app = mod.app
    else:
        app = FastAPI()
        if hasattr(mod, "router"):
            app.include_router(mod.router)
        else:
            # Try to find any APIRouter exported
            for attr in dir(mod):
                obj = getattr(mod, attr)
                try:
                    from fastapi import APIRouter

                    if isinstance(obj, APIRouter):
                        app.include_router(obj)
                        break
                except Exception:
                    pass

    return TestClient(app)


def _make_openai_mock(response_text: str):
    """Create a fake openai module to insert into sys.modules.

    The real code expects a ChatCompletion-like response with
    choices[0].message.content == response_text
    """
    class DummyChatCompletion:
        @staticmethod
        def create(*args, **kwargs):
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=response_text))])

    dummy = SimpleNamespace(ChatCompletion=DummyChatCompletion)

    # Provide a nested error class container used in tests that expect openai.error.APIError
    err_ns = SimpleNamespace(APIError=type("APIError", (Exception,), {}))
    dummy.error = err_ns
    return dummy


def _make_openai_raising(exc: Exception):
    class DummyChatCompletion:
        @staticmethod
        def create(*args, **kwargs):
            raise exc

    dummy = SimpleNamespace(ChatCompletion=DummyChatCompletion)
    err_ns = SimpleNamespace(APIError=type("APIError", (Exception,), {}))
    dummy.error = err_ns
    return dummy


def _refined_idea_json():
    # This JSON should match your project's RefinedIdea schema.
    # Keep it minimal but valid according to the models implemented earlier.
    payload = {
        "idea_title": "Smart Grocery List",
        "problem_statement": "People forget what to buy and overspend.",
        "solution_concept": "An app that builds lists from receipts and habits.",
        "target_user": "Busy parents",
        "core_domain": "consumer-apps",
        "suggested_location": "US",
        "nlp_suggestions": ["add recipe import", "share lists with family"],
        "initial_feasibility_score": 4.0,
    }
    return json.dumps(payload)


def _market_profile_dict(score: float = 4.0):
    return {
        "idea_title": "Smart Grocery List",
        "core_domain": "consumer-apps",
        "suggested_location": "US",
        "market_viability_score": score,
        "community_engagement_score": 0.0,
        "viability_rationale": "Mocked profile for tests",
        "raw_trend_score": 3.9,
        "raw_competitor_count": 5,
    }


def test_happy_path(test_app, monkeypatch):
    mod = _load_validation_module()

    # Insert fake openai into sys.modules so any runtime-import inside the handler uses it
    mock_openai = _make_openai_mock(_refined_idea_json())
    monkeypatch.setitem(sys.modules, "openai", mock_openai)

    # Mock MCP_SERVICE.get_concept_profile to return a good market profile
    mocked_profile = _market_profile_dict(score=4.0)

    if hasattr(mod, "MCP_SERVICE"):
        monkeypatch.setattr(mod.MCP_SERVICE, "get_concept_profile", lambda refined: mocked_profile)
    else:
        pytest.skip("MCP_SERVICE not found in module; check api/validation.py")

    resp = test_app.post("/refine-idea", json={"raw_idea_text": "some idea text"})
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Basic shape checks
    assert "refined_idea" in body
    assert "market_profile" in body
    assert "overall_confidence_score" in body

    overall = float(body["overall_confidence_score"])
    assert overall > 3.0


def test_mcp_failure_degradation(test_app, monkeypatch):
    mod = _load_validation_module()

    mock_openai = _make_openai_mock(_refined_idea_json())
    monkeypatch.setitem(sys.modules, "openai", mock_openai)

    # MCP returns a fallback profile with zeroed market score and a rationale mentioning 'failed'
    fallback = _market_profile_dict(score=0.0)
    fallback["viability_rationale"] = "external fetch failed: timeout"

    if hasattr(mod, "MCP_SERVICE"):
        monkeypatch.setattr(mod.MCP_SERVICE, "get_concept_profile", lambda refined: fallback)
    else:
        pytest.skip("MCP_SERVICE not found in module; check api/validation.py")

    resp = test_app.post("/refine-idea", json={"raw_idea_text": "some idea text"})
    assert resp.status_code == 200, resp.text
    body = resp.json()

    refined = body["refined_idea"]
    feasibility = float(refined.get("initial_feasibility_score", 0.0))
    overall = float(body["overall_confidence_score"])

    # overall should be 0.5*feasibility + 0.5*0.0
    assert abs(overall - (0.5 * feasibility)) < 1e-6
    assert "failed" in body["market_profile"]["viability_rationale"].lower()


def test_llm_failure_returns_500(test_app, monkeypatch):
    mod = _load_validation_module()

    # Make openai raise an APIError during the ChatCompletion call
    dummy_exc = Exception("simulated openai failure")
    mock_openai = _make_openai_raising(dummy_exc)
    monkeypatch.setitem(sys.modules, "openai", mock_openai)

    resp = test_app.post("/refine-idea", json={"raw_idea_text": "some idea text"})

    # The handler is expected to surface an error (HTTP 500); assert that.
    assert resp.status_code == 500
    body = resp.json()
    assert "detail" in body
