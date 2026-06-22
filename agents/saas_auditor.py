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

"""
VendorGuard AI — Agent A: SaaS Auditor
--------------------------------------
Analyzes a vendor's public website to extract security posture indicators,
compliance certificates, hosting regions, and an overall security score
contribution (0–50). Used as part of the UiPath Maestro Case hackathon
VendorGuard AI pipeline.
"""

import os
import re
import time
import logging
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants — keyword lists for signal detection
# ---------------------------------------------------------------------------

# Compliance certificate keywords mapped to canonical certificate names
COMPLIANCE_KEYWORDS: dict[str, str] = {
    "soc 2": "SOC2",
    "soc2": "SOC2",
    "soc ii": "SOC2",
    "iso 27001": "ISO27001",
    "iso27001": "ISO27001",
    "iso/iec 27001": "ISO27001",
    "pci dss": "PCI-DSS",
    "pci-dss": "PCI-DSS",
    "pci compliance": "PCI-DSS",
    "gdpr": "GDPR",
    "general data protection": "GDPR",
    "hipaa": "HIPAA",
    "health insurance portability": "HIPAA",
    "fedramp": "FedRAMP",
    "ccpa": "CCPA",
    "iso 9001": "ISO9001",
    "csa star": "CSA-STAR",
    "nist": "NIST",
}

# Cloud / hosting provider keywords → region labels
HOSTING_KEYWORDS: dict[str, str] = {
    "aws": "AWS",
    "amazon web services": "AWS",
    "amazon s3": "AWS",
    "us-east": "AWS-US",
    "eu-west": "AWS-EU",
    "azure": "Azure",
    "microsoft azure": "Azure",
    "google cloud": "GCP",
    "gcp": "GCP",
    "google cloud platform": "GCP",
    "cloudflare": "Cloudflare",
    "fastly": "Fastly",
    "akamai": "Akamai",
    "digital ocean": "DigitalOcean",
    "digitalocean": "DigitalOcean",
    "heroku": "Heroku",
    "us data center": "US-Region",
    "european data center": "EU-Region",
    "eu data center": "EU-Region",
    "data residency": "Data-Residency",
    "on-premise": "On-Premise",
    "on premise": "On-Premise",
}

# Positive security posture signals
SECURITY_POSITIVE_KEYWORDS: list[str] = [
    "encryption",
    "aes-256",
    "end-to-end",
    "tls",
    "ssl",
    "zero trust",
    "zero-trust",
    "mfa",
    "multi-factor",
    "2fa",
    "two-factor",
    "penetration test",
    "pen test",
    "bug bounty",
    "vulnerability disclosure",
    "security audit",
    "siem",
    "soc",
    "intrusion detection",
    "ids",
    "ips",
    "ddos protection",
    "waf",
    "web application firewall",
    "access control",
    "rbac",
    "role-based",
    "single sign-on",
    "sso",
    "saml",
    "oauth",
    "api key rotation",
    "key management",
    "secret management",
    "vault",
    "incident response",
    "disaster recovery",
    "business continuity",
    "data backup",
    "redundancy",
    "uptime",
    "99.9%",
    "security team",
    "ciso",
    "privacy by design",
    "data minimization",
    "anonymization",
    "pseudonymization",
]

# Negative / risk signals that reduce the score
SECURITY_NEGATIVE_KEYWORDS: list[str] = [
    "no encryption",
    "unencrypted",
    "plain text password",
    "no audit log",
    "shared credentials",
    "no mfa",
]

# Pages most likely to contain security/compliance info
SECURITY_PAGE_PATHS: list[str] = [
    "/security",
    "/security/",
    "/trust",
    "/trust-center",
    "/compliance",
    "/privacy",
    "/privacy-policy",
    "/legal",
    "/terms",
    "/tos",
    "/gdpr",
    "/docs/security",
    "/about/security",
]

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; VendorGuardBot/1.0; "
        "security-audit-research)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}
DEFAULT_TIMEOUT = 12  # seconds


def _is_allowed_by_robots(base_url: str, path: str) -> bool:
    """
    Check whether our user-agent is permitted to fetch the given path
    according to the site's robots.txt. Returns True when uncertain.
    """
    try:
        rp = RobotFileParser()
        rp.set_url(urljoin(base_url, "/robots.txt"))
        rp.read()
        return rp.can_fetch(REQUEST_HEADERS["User-Agent"], urljoin(base_url, path))
    except Exception:
        # If robots.txt is unreachable, be permissive
        return True


def _fetch_html(url: str, timeout: int = DEFAULT_TIMEOUT) -> str | None:
    """
    Fetch raw HTML from a URL. Returns None on any error.
    Respects a polite delay and handles common network failures gracefully.
    """
    try:
        resp = requests.get(
            url,
            headers=REQUEST_HEADERS,
            timeout=timeout,
            allow_redirects=True,
        )
        resp.raise_for_status()
        # Only process HTML responses
        content_type = resp.headers.get("Content-Type", "")
        if "text/html" not in content_type and "text/plain" not in content_type:
            return None
        return resp.text
    except requests.exceptions.Timeout:
        logger.warning("Timeout fetching %s", url)
    except requests.exceptions.ConnectionError:
        logger.warning("Connection error fetching %s", url)
    except requests.exceptions.HTTPError as exc:
        logger.warning("HTTP %s for %s", exc.response.status_code, url)
    except Exception as exc:
        logger.warning("Unexpected error fetching %s: %s", url, exc)
    return None


def _extract_visible_text(html: str) -> str:
    """
    Parse HTML with BeautifulSoup and return lowercased visible text,
    stripping script/style tags.
    """
    soup = BeautifulSoup(html, "html.parser")
    # Remove non-visible elements
    for tag in soup(["script", "style", "noscript", "meta", "head"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)
    return text.lower()


# ---------------------------------------------------------------------------
# LangChain tools
# ---------------------------------------------------------------------------

@tool
def scrape_main_website(website_url: str) -> str:
    """
    Fetches and returns the visible text content of the vendor's main
    homepage. Use this as the first step to get a general overview of
    the vendor's claims, offerings, and any top-level security mentions.

    Args:
        website_url: The full URL of the vendor's homepage (e.g. https://example.com).

    Returns:
        Visible page text (up to 8 000 characters) or an error message.
    """
    html = _fetch_html(website_url)
    if html is None:
        return f"ERROR: Could not fetch {website_url}"
    text = _extract_visible_text(html)
    # Cap to avoid flooding the context window
    return text[:8_000]


@tool
def scrape_security_pages(website_url: str) -> str:
    """
    Systematically attempts to fetch known security, trust, compliance,
    privacy-policy, and terms-of-service sub-pages from the vendor's
    website. Returns the combined visible text from all reachable pages.

    Args:
        website_url: The base URL of the vendor's website (e.g. https://example.com).

    Returns:
        Combined text from security-related pages (up to 12 000 characters)
        or a note that no such pages were found.
    """
    base = website_url.rstrip("/")
    combined: list[str] = []

    for path in SECURITY_PAGE_PATHS:
        # Respect robots.txt
        if not _is_allowed_by_robots(base, path):
            logger.info("robots.txt disallows %s%s", base, path)
            continue

        url = base + path
        html = _fetch_html(url)
        if html is None:
            continue

        text = _extract_visible_text(html)
        if len(text) > 200:  # Skip near-empty pages
            combined.append(f"--- {url} ---\n{text[:3_000]}")

        # Polite crawl delay
        time.sleep(0.5)

    if not combined:
        return "No security/compliance pages found or all returned errors."

    result = "\n\n".join(combined)
    return result[:12_000]


@tool
def detect_compliance_certificates(text: str) -> str:
    """
    Scans a block of text for mentions of compliance certificates and
    security standards such as SOC2, ISO27001, PCI-DSS, GDPR, HIPAA,
    FedRAMP, CCPA, and others.

    Args:
        text: Lowercased visible text scraped from the vendor's website.

    Returns:
        A comma-separated list of detected certificate names, or
        'NONE_DETECTED' if nothing was found.
    """
    found: set[str] = set()
    lower_text = text.lower()
    for keyword, cert_name in COMPLIANCE_KEYWORDS.items():
        if keyword in lower_text:
            found.add(cert_name)

    if not found:
        return "NONE_DETECTED"
    return ", ".join(sorted(found))


@tool
def detect_hosting_regions(text: str) -> str:
    """
    Scans a block of text for mentions of cloud providers and hosting
    regions such as AWS, Azure, GCP, Cloudflare, EU data centers, etc.

    Args:
        text: Lowercased visible text scraped from the vendor's website.

    Returns:
        A comma-separated list of detected hosting region/provider labels,
        or 'UNKNOWN' if nothing was found.
    """
    found: set[str] = set()
    lower_text = text.lower()
    for keyword, label in HOSTING_KEYWORDS.items():
        if keyword in lower_text:
            found.add(label)

    if not found:
        return "UNKNOWN"
    return ", ".join(sorted(found))


@tool
def score_security_posture(text: str) -> str:
    """
    Evaluates the security posture of a vendor by counting positive and
    negative security signal keywords in the provided text. Returns an
    integer score contribution between 0 and 50 as a string.

    Scoring logic:
      - Each unique positive keyword hit adds points (diminishing returns).
      - Each negative keyword hit subtracts points.
      - Score is clamped to [0, 50].

    Args:
        text: Lowercased visible text scraped from the vendor's website.

    Returns:
        An integer string between '0' and '50'.
    """
    lower_text = text.lower()

    positive_hits: list[str] = [kw for kw in SECURITY_POSITIVE_KEYWORDS if kw in lower_text]
    negative_hits: list[str] = [kw for kw in SECURITY_NEGATIVE_KEYWORDS if kw in lower_text]

    # Positive scoring: first 5 hits worth 5pts each, next 5 worth 2pts each, rest 1pt
    score = 0
    for i, _ in enumerate(positive_hits):
        if i < 5:
            score += 5
        elif i < 10:
            score += 2
        else:
            score += 1

    # Negative scoring: each red-flag keyword removes 5 pts
    score -= len(negative_hits) * 5

    # Clamp
    score = max(0, min(50, score))
    return str(score)


# ---------------------------------------------------------------------------
# Agent prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are VendorGuard Agent A — a security analyst that evaluates SaaS vendors
based on their public website.

Follow this exact sequence when given a vendor name and URL:
1. Call scrape_main_website to get the homepage content.
2. Call scrape_security_pages to get security/compliance sub-pages.
3. Combine all text and call detect_compliance_certificates.
4. Call detect_hosting_regions on the combined text.
5. Call score_security_posture on the combined text.
6. Return a FINAL ANSWER in this exact format (no extra commentary):

FINDINGS: <semicolon-separated list of key security observations>
COMPLIANCE_CERTS: <comma-separated cert names, or NONE>
HOSTING_REGIONS: <comma-separated values, or UNKNOWN>
SECURITY_SCORE: <integer 0-50>
"""


# ---------------------------------------------------------------------------
# SaaSAuditorAgent
# ---------------------------------------------------------------------------

class SaaSAuditorAgent:
    """
    Agent A of VendorGuard AI.

    Uses a LangChain ReAct agent backed by Groq's llama-3.3-70b-versatile
    to crawl a vendor's public website and extract:
      - Security posture findings (list of strings)
      - Compliance certificates detected (list)
      - Hosting regions / cloud providers (list)
      - Security score contribution (int 0–50)
    """

    # Groq model — fast and capable for structured extraction tasks
    GROQ_MODEL = "llama-3.3-70b-versatile"

    def __init__(self) -> None:
        self._llm: ChatGroq | None = None
        self._agent = None

    def _get_agent(self):
        """Build (or return cached) the LangGraph ReAct agent."""
        if self._agent is not None:
            return self._agent

        self._llm = ChatGroq(
            model=self.GROQ_MODEL,
            temperature=0,
            groq_api_key=os.getenv("GROQ_API_KEY"),
        )

        tools = [
            scrape_main_website,
            scrape_security_pages,
            detect_compliance_certificates,
            detect_hosting_regions,
            score_security_posture,
        ]

        self._agent = create_react_agent(
            self._llm,
            tools,
            prompt=SystemMessage(content=SYSTEM_PROMPT),
        )
        return self._agent

    # ------------------------------------------------------------------
    # Response parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_list(raw: str) -> list[str]:
        """Split a semicolon- or comma-separated string into a clean list."""
        if not raw or raw.strip().upper() in ("NONE", "UNKNOWN", "NONE_DETECTED"):
            return []
        # Try semicolons first (used for findings), then commas
        sep = ";" if ";" in raw else ","
        return [item.strip() for item in raw.split(sep) if item.strip()]

    @staticmethod
    def _parse_score(raw: str) -> int:
        """Extract integer score from the LLM output string; default 0."""
        match = re.search(r"\d+", raw)
        if match:
            return max(0, min(50, int(match.group())))
        return 0

    def _parse_final_answer(self, output: str) -> dict[str, Any]:
        """
        Parse the structured FINAL ANSWER block emitted by the ReAct agent
        into a typed dict. Falls back gracefully if parsing fails.
        """
        result: dict[str, Any] = {
            "findings": [],
            "compliance_certs": [],
            "hosting_regions": [],
            "security_score_contribution": 0,
        }

        # Extract each field with regex
        findings_match = re.search(r"FINDINGS:\s*(.+?)(?:\n|$)", output, re.IGNORECASE)
        certs_match = re.search(r"COMPLIANCE_CERTS:\s*(.+?)(?:\n|$)", output, re.IGNORECASE)
        regions_match = re.search(r"HOSTING_REGIONS:\s*(.+?)(?:\n|$)", output, re.IGNORECASE)
        score_match = re.search(r"SECURITY_SCORE:\s*(\d+)", output, re.IGNORECASE)

        if findings_match:
            result["findings"] = self._parse_list(findings_match.group(1))
        if certs_match:
            raw_certs = certs_match.group(1).strip()
            result["compliance_certs"] = self._parse_list(raw_certs) if raw_certs.upper() not in ("NONE", "NONE_DETECTED") else []
        if regions_match:
            raw_regions = regions_match.group(1).strip()
            result["hosting_regions"] = self._parse_list(raw_regions) if raw_regions.upper() != "UNKNOWN" else []
        if score_match:
            result["security_score_contribution"] = self._parse_score(score_match.group(1))

        return result

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, vendor_name: str, website: str) -> dict[str, Any]:
        """
        Analyze a vendor's public website for security signals.

        Args:
            vendor_name: Human-readable vendor name (e.g. "Acme Corp").
            website:     Full base URL of the vendor's website
                         (e.g. "https://acmecorp.com").

        Returns:
            A dict with keys:
              - findings (list[str])          : security observations
              - compliance_certs (list[str])  : detected certs (SOC2, ISO27001 …)
              - hosting_regions (list[str])   : cloud providers / regions
              - security_score_contribution (int 0–50)

        Raises:
            ValueError: If website URL is missing or malformed.
            RuntimeError: If the GROQ_API_KEY env var is not set.
        """
        # --- Input validation ---
        if not website:
            raise ValueError("website URL must not be empty")
        parsed = urlparse(website)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"website must start with http:// or https://, got: {website!r}")
        if not os.getenv("GROQ_API_KEY"):
            raise RuntimeError("GROQ_API_KEY environment variable is not set")

        logger.info("Starting VendorGuard analysis for %s (%s)", vendor_name, website)

        # --- Run the agent ---
        try:
            agent = self._get_agent()
            human_msg = f"Analyze vendor '{vendor_name}' at {website}."
            response = agent.invoke({"messages": [("human", human_msg)]})
            raw_output: str = response["messages"][-1].content
        except Exception as exc:
            # Log and return a safe fallback rather than crashing the pipeline
            logger.error("Agent execution failed for %s: %s", vendor_name, exc)
            return {
                "findings": [f"Analysis failed: {exc}"],
                "compliance_certs": [],
                "hosting_regions": [],
                "security_score_contribution": 0,
            }

        logger.info("Agent finished. Parsing output for %s.", vendor_name)
        result = self._parse_final_answer(raw_output)
        logger.info("Result for %s: %s", vendor_name, result)
        return result


# ---------------------------------------------------------------------------
# Quick smoke-test (run directly: python saas_auditor.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO)

    agent = SaaSAuditorAgent()
    test_vendor = "Stripe"
    test_url = "https://stripe.com"

    print(f"\nAnalyzing {test_vendor} at {test_url} ...\n")
    output = agent.analyze(vendor_name=test_vendor, website=test_url)
    print("\n=== VendorGuard Result ===")
    print(json.dumps(output, indent=2))
