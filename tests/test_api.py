# MIT License — Copyright (c) 2026 VendorGuard AI

"""
Basic smoke tests for VendorGuard AI API.
Run with: pytest tests/test_api.py -v
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from api.main import app, _generate_mock_response, _is_mock_mode

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "mode" in data


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "VendorGuard AI"
    assert "UiPath Maestro Case" in data["tracks"]
    assert "mode" in data


def test_mock_mode_detection():
    import os
    original = os.environ.get("GROQ_API_KEY")
    try:
        os.environ["GROQ_API_KEY"] = "placeholder"
        assert _is_mock_mode() is True
        os.environ["GROQ_API_KEY"] = ""
        assert _is_mock_mode() is True
    finally:
        if original is None:
            os.environ.pop("GROQ_API_KEY", None)
        else:
            os.environ["GROQ_API_KEY"] = original


def test_mock_microsoft_profile():
    saas, threat = _generate_mock_response("Microsoft", "https://microsoft.com")
    assert saas["security_score_contribution"] >= 40
    assert "SOC2" in saas["compliance_certs"]
    assert threat["requires_human_review"] is False


def test_mock_unknown_vendor_https():
    saas, threat = _generate_mock_response("SomeRandomCorp", "https://somecorp.io")
    assert isinstance(saas["security_score_contribution"], int)
    assert isinstance(threat["threat_score_contribution"], int)


def test_mock_risky_vendor():
    saas, threat = _generate_mock_response("free crack hack tool", "http://sketchy.net")
    combined = saas["security_score_contribution"] + threat["threat_score_contribution"]
    assert combined < 50
    assert threat["requires_human_review"] is True


def test_analyze_vendor_mock_mode():
    """In mock mode (no real key), the Microsoft profile should return a high score."""
    import os
    os.environ.setdefault("GROQ_API_KEY", "placeholder")

    response = client.post(
        "/analyze-vendor",
        json={"vendor_name": "Microsoft", "website": "https://microsoft.com"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["vendor_name"] == "Microsoft"
    assert data["security_score"] >= 70
    assert data["requires_human_review"] is False
    assert "timestamp" in data
    assert data["mode"] in ("mock", "live", "mock-fallback")


def test_analyze_vendor_missing_feature():
    response = client.post(
        "/analyze-vendor",
        json={"vendor_name": "TestCorp"},
    )
    assert response.status_code == 422  # Validation error — missing website


def test_analyze_vendor_high_risk():
    """Risky vendor keywords should trigger human review."""
    import os
    os.environ.setdefault("GROQ_API_KEY", "placeholder")

    response = client.post(
        "/analyze-vendor",
        json={"vendor_name": "free hack tool", "website": "http://sketchycorp.net"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["security_score"] < 50
    assert data["requires_human_review"] is True
