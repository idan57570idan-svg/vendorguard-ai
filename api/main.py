# MIT License
#
# Copyright (c) 2025 VendorGuard AI
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
import sys
from datetime import datetime, timezone
from typing import Any

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
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
# App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("VendorGuard AI is up — POST /analyze-vendor to begin.")
    yield

app = FastAPI(
    title="VendorGuard AI",
    description="Automated vendor security analysis powered by AI agents.",
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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/")
async def root() -> dict:
    return {
        "name": "VendorGuard AI",
        "version": "1.0.0",
        "tracks": ["UiPath Maestro Case"],
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "VendorGuard AI"}


@app.post("/analyze-vendor", response_model=VendorResponse)
async def analyze_vendor(request: VendorRequest) -> VendorResponse:
    logger.info(
        "Starting vendor analysis: vendor=%s website=%s",
        request.vendor_name,
        request.website,
    )

    try:
        # --- SaaS audit agent ---
        saas_agent = SaaSAuditorAgent()
        saas_result: dict = saas_agent.analyze(
            vendor_name=request.vendor_name,
            website=request.website,
        )
        logger.info("SaaS audit complete: %s", saas_result)

        # --- Threat intel agent ---
        threat_agent = ThreatIntelAgent()
        threat_result: dict = threat_agent.analyze(
            vendor_name=request.vendor_name,
            website=request.website,
        )
        logger.info("Threat intel complete: %s", threat_result)

    except Exception as exc:
        logger.exception("Agent execution failed")
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {exc}") from exc

    # --- Combine scores (clamped to 1–100) ---
    raw_score = (
        saas_result.get("security_score_contribution", 0)
        + threat_result.get("threat_score_contribution", 0)
    )
    security_score = max(1, min(100, raw_score))

    # --- Aggregate findings (threat_intel uses "threat_findings" key) ---
    key_findings: list[str] = (
        saas_result.get("findings", [])
        + threat_result.get("threat_findings", threat_result.get("findings", []))
    )

    # Flag for human review: low score, agent flagged it, or critical findings
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
        "Analysis complete: vendor=%s score=%d review_required=%s",
        request.vendor_name,
        security_score,
        requires_human_review,
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
    )


