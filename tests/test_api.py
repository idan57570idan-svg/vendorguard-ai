# MIT License — Copyright (c) 2026 VendorGuard AI

"""
Basic smoke tests for VendorGuard AI API.
Run with: pytest tests/test_api.py -v
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from api.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "VendorGuard AI"
    assert "UiPath Maestro Case" in data["tracks"]


def test_analyze_vendor_mock():
    mock_saas = {
        "findings": ["SOC2 detected", "Hosted on AWS"],
        "compliance_certs": ["SOC2"],
        "hosting_regions": ["AWS US-East"],
        "security_score_contribution": 40,
    }
    mock_threat = {
        "threat_findings": ["No breach history found"],
        "breach_history": [],
        "bug_bounty_exposure": {"platform": "HackerOne", "open_count": 3},
        "threat_score_contribution": 35,
        "requires_human_review": False,
    }

    with patch("api.main.SaaSAuditorAgent") as MockSaaS, \
         patch("api.main.ThreatIntelAgent") as MockThreat:
        MockSaaS.return_value.analyze.return_value = mock_saas
        MockThreat.return_value.analyze.return_value = mock_threat

        response = client.post(
            "/analyze-vendor",
            json={"vendor_name": "TestCorp", "website": "https://testcorp.com"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["vendor_name"] == "TestCorp"
    assert data["security_score"] == 75  # 40 + 35
    assert data["requires_human_review"] is False
    assert "SOC2 detected" in data["key_findings"]
    assert "No breach history found" in data["key_findings"]
    assert "timestamp" in data


def test_analyze_vendor_missing_feature():
    response = client.post(
        "/analyze-vendor",
        json={"vendor_name": "TestCorp"},
    )
    assert response.status_code == 422  # Validation error — missing website


def test_analyze_vendor_high_risk():
    mock_saas = {
        "findings": ["No compliance certs found", "HTTP only (no HTTPS)"],
        "compliance_certs": [],
        "hosting_regions": [],
        "security_score_contribution": 10,
    }
    mock_threat = {
        "threat_findings": ["CRITICAL: breach detected in 2023"],
        "breach_history": [{"year": 2023, "records": 10000}],
        "bug_bounty_exposure": {"platform": None, "open_count": 0},
        "threat_score_contribution": 5,
        "requires_human_review": True,
    }

    with patch("api.main.SaaSAuditorAgent") as MockSaaS, \
         patch("api.main.ThreatIntelAgent") as MockThreat:
        MockSaaS.return_value.analyze.return_value = mock_saas
        MockThreat.return_value.analyze.return_value = mock_threat

        response = client.post(
            "/analyze-vendor",
            json={"vendor_name": "SketchyCorp", "website": "http://sketchycorp.net"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["security_score"] == 15  # 10 + 5
    assert data["requires_human_review"] is True  # score < 50 AND "breach" in findings
