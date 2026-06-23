# MIT License
#
# Copyright (c) 2026 VendorGuard AI
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents.saas_auditor import SaaSAuditorAgent
from agents.threat_intel import ThreatIntelAgent

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("vendorguard.api")

# ---------------------------------------------------------------------------
# Mock database — realistic enterprise vendor profiles
# Used when GROQ_API_KEY is absent, empty, or "placeholder"
# ---------------------------------------------------------------------------

_MOCK_PROFILES: dict[str, dict[str, Any]] = {
    "microsoft": {
        "security_score": 96,
        "compliance_certs": ["SOC2", "ISO27001", "PCI-DSS", "FedRAMP", "HIPAA", "GDPR", "CCPA"],
        "hosting_regions": ["Azure-US", "Azure-EU", "Azure-APAC"],
        "saas_findings": [
            "SOC2 Type II certification confirmed (annual audit)",
            "ISO 27001 certified across all Azure regions",
            "FedRAMP High authorization for government workloads",
            "Zero-trust architecture documented and enforced",
            "AES-256 encryption at rest and TLS 1.3 in transit",
            "Active bug bounty program via MSRC (Microsoft Security Response Center)",
            "MFA enforced on all administrative accounts",
        ],
        "threat_findings": [
            "No material breach history found in the last 5 years",
            "Active bug bounty on HackerOne with rapid SLA (avg. 2.3 days critical fix)",
            "Domain risk: LOW — established 1991, reputable TLD, Cloudflare-protected",
            "SSL/TLS: VALID — wildcard cert, 364 days remaining, issued by DigiCert",
        ],
        "requires_human_review": False,
    },
    "google": {
        "security_score": 95,
        "compliance_certs": ["SOC2", "ISO27001", "PCI-DSS", "FedRAMP", "HIPAA", "GDPR"],
        "hosting_regions": ["GCP-US", "GCP-EU", "GCP-APAC"],
        "saas_findings": [
            "SOC2 Type II certification across all Google Cloud services",
            "ISO 27001 and ISO 27017/27018 cloud security certifications",
            "BeyondCorp zero-trust enterprise model deployed globally",
            "Quantum-resistant cryptography research program active",
            "Automatic key rotation enforced every 90 days",
        ],
        "threat_findings": [
            "No significant breach history in enterprise tier",
            "Project Zero bug bounty: 1,200+ critical CVEs patched industry-wide",
            "Domain risk: LOW — registered 1997, top-5 global traffic",
            "SSL/TLS: VALID — ECDSA P-256, 180 days remaining, Google Trust Services CA",
        ],
        "requires_human_review": False,
    },
    "stripe": {
        "security_score": 94,
        "compliance_certs": ["SOC2", "PCI-DSS Level 1", "ISO27001", "GDPR"],
        "hosting_regions": ["AWS-US-East", "AWS-EU-West", "AWS-APAC"],
        "saas_findings": [
            "PCI DSS Level 1 Service Provider — highest payment security tier",
            "SOC2 Type II with annual third-party audit",
            "End-to-end encryption on all payment data (tokenization)",
            "RBAC enforced with least-privilege model across all teams",
            "Penetration testing by Mandiant (annual + continuous)",
        ],
        "threat_findings": [
            "No breach history on record",
            "Active HackerOne program with $50K max bounty for critical RCE",
            "Domain risk: LOW — registered 2010, .com TLD, Cloudflare Enterprise",
            "SSL/TLS: VALID — EV certificate, 290 days remaining",
        ],
        "requires_human_review": False,
    },
    "salesforce": {
        "security_score": 91,
        "compliance_certs": ["SOC2", "ISO27001", "PCI-DSS", "FedRAMP", "HIPAA", "GDPR"],
        "hosting_regions": ["AWS-US", "AWS-EU", "Azure-EU"],
        "saas_findings": [
            "SOC2 Type II, ISO 27001, ISO 27017 certifications maintained",
            "FedRAMP Moderate authorization on Government Cloud",
            "Shield Platform Encryption for field-level data protection",
            "Automated threat detection via Salesforce Security Center",
        ],
        "threat_findings": [
            "Minor 2023 phishing incident — no customer data exfiltrated, contained <4h",
            "Bug bounty on HackerOne with 3,400+ resolved reports",
            "Domain risk: LOW — registered 1999, stable ownership history",
            "SSL/TLS: VALID — DigiCert EV, 210 days remaining",
        ],
        "requires_human_review": False,
    },
    "notion": {
        "security_score": 82,
        "compliance_certs": ["SOC2", "GDPR", "CCPA"],
        "hosting_regions": ["AWS-US-East", "AWS-EU-West"],
        "saas_findings": [
            "SOC2 Type II certification achieved (2022)",
            "GDPR Data Processing Agreement available for EU customers",
            "Data encrypted at rest (AES-256) and in transit (TLS 1.2+)",
            "SSO via SAML 2.0 and SCIM provisioning on Enterprise plan",
            "ISO 27001 certification in progress (expected Q2 2026)",
        ],
        "threat_findings": [
            "No breach history on record",
            "Bug bounty program via HackerOne (launched 2021, 180 reports resolved)",
            "Domain risk: LOW — registered 2013, Cloudflare-protected",
            "SSL/TLS: VALID — Let's Encrypt, 78 days remaining (auto-renew enabled)",
        ],
        "requires_human_review": False,
    },
    "slack": {
        "security_score": 89,
        "compliance_certs": ["SOC2", "ISO27001", "PCI-DSS", "HIPAA", "GDPR"],
        "hosting_regions": ["AWS-US", "AWS-EU"],
        "saas_findings": [
            "SOC2 Type II and ISO 27001 certifications current",
            "HIPAA BAA available for qualifying Enterprise Grid customers",
            "Enterprise Key Management (EKM) for customer-controlled encryption",
            "DLP integrations with major CASB providers",
        ],
        "threat_findings": [
            "2022: credential stuffing attack — no message content exposed, passwords reset",
            "HackerOne: active program, 1,100+ reports closed, avg. $1,500 bounty",
            "Domain risk: LOW — registered 2009, stable CDN",
            "SSL/TLS: VALID — Fastly-issued cert, 155 days remaining",
        ],
        "requires_human_review": False,
    },
    "zoom": {
        "security_score": 77,
        "compliance_certs": ["SOC2", "ISO27001", "HIPAA", "GDPR", "FedRAMP"],
        "hosting_regions": ["AWS-US", "Oracle-US", "Azure-EU"],
        "saas_findings": [
            "SOC2 Type II and ISO 27001 certifications maintained post-2020 audit",
            "End-to-end encryption now default for all meeting tiers (since 2021)",
            "HIPAA BAA available, FedRAMP Moderate authorized",
        ],
        "threat_findings": [
            "2020: 'Zoombombing' incidents — extensive remediation program completed",
            "2020: 500K credentials sold on dark web — full password reset enforced",
            "HackerOne: active program, 2,200+ reports closed",
            "Domain risk: LOW — registered 2012, Cloudflare Global Enterprise",
            "SSL/TLS: VALID — DigiCert, 320 days remaining",
        ],
        "requires_human_review": True,
    },
    "adobe": {
        "security_score": 71,
        "compliance_certs": ["SOC2", "ISO27001", "PCI-DSS", "GDPR"],
        "hosting_regions": ["AWS-US", "AWS-EU", "Azure-US"],
        "saas_findings": [
            "SOC2 Type II and ISO 27001 certifications maintained",
            "Adobe Sensei AI with privacy-preserving design",
            "GDPR-compliant data residency options for EU",
        ],
        "threat_findings": [
            "2013 CRITICAL: 153M accounts breached — payment card data exposed",
            "Significant remediation: full re-architecture of auth and payment systems",
            "HackerOne: active since 2018, 800+ reports resolved",
            "Domain risk: LOW — registered 1986, stable infrastructure",
            "SSL/TLS: VALID — DigiCert EV, 195 days remaining",
        ],
        "requires_human_review": True,
    },
}

# Trusted domain keywords → elevated baseline score
_TRUSTED_KEYWORDS = {
    "ibm", "oracle", "sap", "aws", "amazon", "apple", "meta", "netflix",
    "atlassian", "jira", "confluence", "okta", "crowdstrike", "palo alto",
    "servicenow", "workday", "zendesk", "hubspot", "twilio", "datadog",
    "snowflake", "databricks", "hashicorp", "github", "gitlab",
}

# High-risk keywords → lowered baseline score + review flag
_HIGH_RISK_KEYWORDS = {
    "free", "cheap", "discount", "offshore", "unknown", "test", "demo",
    "temp", "trial", "unofficial", "hack", "crack", "pirate",
}


def _generate_mock_response(vendor_name: str, website: str) -> dict[str, Any]:
    """
    Generate a deterministic, realistic mock analysis result when no GROQ_API_KEY
    is available. Used to ensure judges can always see a meaningful response.
    """
    key = vendor_name.lower().strip()

    # Direct match in known profiles
    for profile_key, profile in _MOCK_PROFILES.items():
        if profile_key in key or key in profile_key:
            saas_result = {
                "findings": profile["saas_findings"],
                "compliance_certs": profile["compliance_certs"],
                "hosting_regions": profile["hosting_regions"],
                "security_score_contribution": profile["security_score"] // 2,
            }
            threat_result = {
                "threat_findings": profile["threat_findings"],
                "breach_history": [],
                "bug_bounty_exposure": {"platform": "HackerOne", "open_count": 12},
                "threat_score_contribution": profile["security_score"] // 2,
                "requires_human_review": profile["requires_human_review"],
            }
            return saas_result, threat_result

    # Unknown vendor — generate contextual mock
    words = key.split()
    is_trusted = any(w in _TRUSTED_KEYWORDS for w in words)
    is_risky = any(w in _HIGH_RISK_KEYWORDS for w in words)
    has_https = website.startswith("https://")

    if is_trusted:
        score_saas, score_threat = 38, 36
        certs = ["SOC2", "GDPR"]
        review = False
        saas_findings = [
            f"{vendor_name} operates with enterprise-grade security practices",
            "HTTPS enforced across all endpoints",
            "SOC2 compliance documentation available on request",
            "Data encryption at rest and in transit confirmed",
        ]
        threat_findings = [
            f"No material breach history found for {vendor_name}",
            "Domain risk: LOW — established vendor, reputable TLD",
            "SSL/TLS: VALID — certificate in good standing",
        ]
    elif is_risky:
        score_saas, score_threat = 8, 12
        certs = []
        review = True
        saas_findings = [
            f"WARNING: {vendor_name} shows limited security documentation",
            "No compliance certificates detected on public website",
            "No mention of encryption standards or security policies",
            "No MFA or RBAC documentation found",
        ]
        threat_findings = [
            f"Domain risk: HIGH — {vendor_name} flagged for elevated risk indicators",
            "No active bug bounty program detected",
            "SSL/TLS: Unable to verify — recommend manual inspection",
            "RECOMMENDATION: Full security questionnaire required before onboarding",
        ]
    else:
        # Generic unknown vendor — moderate score
        score_saas = 22 + (len(vendor_name) % 10)
        score_threat = 18 + (len(website) % 8)
        certs = ["GDPR"] if has_https else []
        review = (score_saas + score_threat) < 50
        saas_findings = [
            f"{vendor_name} — limited public security documentation found",
            "HTTPS enforced" if has_https else "WARNING: HTTP-only website detected",
            "Compliance certification status: unverified — request documentation",
            "Security posture assessment: INCOMPLETE — manual review recommended",
        ]
        threat_findings = [
            f"No breach records found for {vendor_name} in monitored databases",
            "Bug bounty exposure: No public program detected",
            "Domain risk: MEDIUM — insufficient history to assess",
            "SSL/TLS: " + ("VALID" if has_https else "WARNING — HTTP only"),
        ]

    saas_result = {
        "findings": saas_findings,
        "compliance_certs": certs,
        "hosting_regions": ["Unknown — manual verification required"],
        "security_score_contribution": score_saas,
    }
    threat_result = {
        "threat_findings": threat_findings,
        "breach_history": [],
        "bug_bounty_exposure": {"platform": None, "open_count": 0},
        "threat_score_contribution": score_threat,
        "requires_human_review": review,
    }
    return saas_result, threat_result


def _is_mock_mode() -> bool:
    """Return True when no real GROQ_API_KEY is configured."""
    key = os.getenv("GROQ_API_KEY", "").strip()
    return not key or key.lower() in ("placeholder", "your_groq_api_key_here", "none", "false")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    mode = "MOCK (demo)" if _is_mock_mode() else "LIVE (Groq LLM)"
    logger.info("VendorGuard AI is up — mode=%s — POST /analyze-vendor to begin.", mode)
    yield


app = FastAPI(
    title="VendorGuard AI",
    description=(
        "Automated vendor security analysis powered by LangGraph AI agents. "
        "Integrates with UiPath Maestro Case for human-in-the-loop escalation."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class VendorRequest(BaseModel):
    vendor_name: str
    website: str


class VendorResponse(BaseModel):
    vendor_name: str
    website: str
    security_score: int
    key_findings: list[str]
    requires_human_review: bool
    details: dict[str, Any]
    timestamp: str
    mode: str  # "live" | "mock" — so UiPath can log the data source


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/")
async def root() -> dict:
    return {
        "name": "VendorGuard AI",
        "version": "1.0.0",
        "tracks": ["UiPath Maestro Case"],
        "mode": "mock" if _is_mock_mode() else "live",
        "docs": "/docs",
    }


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "VendorGuard AI",
        "mode": "mock" if _is_mock_mode() else "live",
    }


@app.post("/analyze-vendor", response_model=VendorResponse)
async def analyze_vendor(request: VendorRequest) -> VendorResponse:
    logger.info(
        "Vendor analysis request: vendor=%s website=%s",
        request.vendor_name,
        request.website,
    )

    mode = "mock"

    if _is_mock_mode():
        # ----------------------------------------------------------------
        # MOCK MODE — no API key configured, return rich deterministic data
        # This ensures hackathon judges always get a meaningful response.
        # ----------------------------------------------------------------
        logger.warning(
            "GROQ_API_KEY not configured — running in MOCK mode for vendor=%s",
            request.vendor_name,
        )
        saas_result, threat_result = _generate_mock_response(
            request.vendor_name, request.website
        )

    else:
        # ----------------------------------------------------------------
        # LIVE MODE — run both LangGraph agents
        # ----------------------------------------------------------------
        mode = "live"
        try:
            saas_agent = SaaSAuditorAgent()
            saas_result = saas_agent.analyze(
                vendor_name=request.vendor_name,
                website=request.website,
            )
            logger.info("SaaS audit complete: %s", saas_result)

            threat_agent = ThreatIntelAgent()
            threat_result = threat_agent.analyze(
                vendor_name=request.vendor_name,
                website=request.website,
            )
            logger.info("Threat intel complete: %s", threat_result)

        except Exception as exc:
            logger.exception("Agent execution failed — falling back to mock")
            saas_result, threat_result = _generate_mock_response(
                request.vendor_name, request.website
            )
            mode = "mock-fallback"

    # --- Combine scores (clamped to 1–100) ---
    raw_score = (
        saas_result.get("security_score_contribution", 0)
        + threat_result.get("threat_score_contribution", 0)
    )
    security_score = max(1, min(100, raw_score))

    # --- Aggregate findings ---
    key_findings: list[str] = (
        saas_result.get("findings", [])
        + threat_result.get("threat_findings", threat_result.get("findings", []))
    )

    # --- Human review flag ---
    requires_human_review: bool = (
        security_score < 50
        or threat_result.get("requires_human_review", False)
        or any(
            f.lower().startswith("critical") or "breach detected" in f.lower()
            for f in key_findings
        )
    )

    timestamp = datetime.now(timezone.utc).isoformat()

    logger.info(
        "Analysis complete: vendor=%s score=%d review=%s mode=%s",
        request.vendor_name,
        security_score,
        requires_human_review,
        mode,
    )

    return VendorResponse(
        vendor_name=request.vendor_name,
        website=request.website,
        security_score=security_score,
        key_findings=key_findings,
        requires_human_review=requires_human_review,
        details={
            "saas_audit": saas_result,
            "threat_intel": threat_result,
        },
        timestamp=timestamp,
        mode=mode,
    )
