# MIT License
#
# Copyright (c) 2026 VendorGuard Contributors
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
VendorGuard — Agent B: Threat Intelligence Agent
=================================================
Simulates threat intelligence gathering for a vendor using LangChain tools
backed by a Groq LLM (llama-3.3-70b-versatile).

Checks performed:
  1. Breach database lookup (simulated with known-breach mock data)
  2. Bug bounty exposure (HackerOne / Bugcrowd pattern matching)
  3. Domain age / WHOIS-like risk analysis
  4. SSL/TLS certificate validity via live HTTPS request

Returns a structured dict suitable for downstream risk scoring in VendorGuard.
"""

import os
import re
import ssl
import socket
import datetime
from typing import Any
from urllib.parse import urlparse

import requests
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent


# ---------------------------------------------------------------------------
# Mock breach database
# Known-breached companies and their incident details (simulated data).
# In a real system this would query HaveIBeenPwned, SpyCloud, or similar APIs.
# ---------------------------------------------------------------------------
_BREACH_DB: dict[str, list[dict[str, Any]]] = {
    "adobe": [
        {
            "date": "2013-10-03",
            "records_affected": 153_000_000,
            "data_types": ["email", "encrypted_password", "payment_card"],
            "description": "Adobe suffered a massive breach exposing customer credentials and payment data.",
        }
    ],
    "yahoo": [
        {
            "date": "2013-08-01",
            "records_affected": 3_000_000_000,
            "data_types": ["email", "password_hash", "security_questions", "dob"],
            "description": "All Yahoo accounts were compromised in a state-sponsored attack.",
        },
        {
            "date": "2014-09-22",
            "records_affected": 500_000_000,
            "data_types": ["email", "password_hash", "phone", "dob"],
            "description": "A separate breach later disclosed affected 500M Yahoo accounts.",
        },
    ],
    "linkedin": [
        {
            "date": "2012-06-05",
            "records_affected": 117_000_000,
            "data_types": ["email", "password_hash"],
            "description": "LinkedIn password hashes leaked; 117M credentials circulated publicly.",
        }
    ],
    "equifax": [
        {
            "date": "2017-09-07",
            "records_affected": 147_900_000,
            "data_types": ["ssn", "dob", "address", "credit_history"],
            "description": "Equifax exposed highly sensitive consumer financial data.",
        }
    ],
    "marriott": [
        {
            "date": "2018-11-30",
            "records_affected": 500_000_000,
            "data_types": ["passport_number", "email", "payment_card", "dob"],
            "description": "Starwood (Marriott) reservation database breached; guest records exposed.",
        }
    ],
    "target": [
        {
            "date": "2013-12-19",
            "records_affected": 110_000_000,
            "data_types": ["payment_card", "email", "phone"],
            "description": "Point-of-sale malware compromised Target payment systems.",
        }
    ],
    "uber": [
        {
            "date": "2016-11-22",
            "records_affected": 57_000_000,
            "data_types": ["email", "phone", "name", "driver_license"],
            "description": "Uber paid attackers to delete stolen data and concealed the breach.",
        }
    ],
    "dropbox": [
        {
            "date": "2012-07-01",
            "records_affected": 68_000_000,
            "data_types": ["email", "password_hash"],
            "description": "Dropbox credential database stolen; hashes published years later.",
        }
    ],
    "twitter": [
        {
            "date": "2022-07-22",
            "records_affected": 5_400_000,
            "data_types": ["email", "phone", "username"],
            "description": "API vulnerability exposed Twitter user account data.",
        }
    ],
    "lastpass": [
        {
            "date": "2022-08-25",
            "records_affected": 33_000_000,
            "data_types": ["password_vault", "email", "billing_address"],
            "description": "LastPass vaults (encrypted) and account metadata stolen.",
        }
    ],
}

# ---------------------------------------------------------------------------
# Mock bug bounty registry
# Maps known program participants by company name pattern to simulated stats.
# ---------------------------------------------------------------------------
_BUG_BOUNTY_REGISTRY: dict[str, dict[str, Any]] = {
    "google": {"platform": "HackerOne", "open_critical": 3, "open_total": 47},
    "microsoft": {"platform": "HackerOne", "open_critical": 5, "open_total": 82},
    "apple": {"platform": "HackerOne", "open_critical": 2, "open_total": 19},
    "facebook": {"platform": "HackerOne", "open_critical": 4, "open_total": 61},
    "meta": {"platform": "HackerOne", "open_critical": 4, "open_total": 61},
    "twitter": {"platform": "HackerOne", "open_critical": 7, "open_total": 34},
    "x.com": {"platform": "HackerOne", "open_critical": 7, "open_total": 34},
    "shopify": {"platform": "HackerOne", "open_critical": 1, "open_total": 22},
    "github": {"platform": "HackerOne", "open_critical": 0, "open_total": 15},
    "stripe": {"platform": "HackerOne", "open_critical": 0, "open_total": 8},
    "uber": {"platform": "HackerOne", "open_critical": 6, "open_total": 29},
    "airbnb": {"platform": "HackerOne", "open_critical": 2, "open_total": 18},
    "dropbox": {"platform": "HackerOne", "open_critical": 1, "open_total": 11},
    "paypal": {"platform": "HackerOne", "open_critical": 3, "open_total": 25},
    "adobe": {"platform": "HackerOne", "open_critical": 4, "open_total": 37},
    "netflix": {"platform": "Bugcrowd", "open_critical": 2, "open_total": 14},
    "salesforce": {"platform": "HackerOne", "open_critical": 1, "open_total": 20},
    "twitter": {"platform": "HackerOne", "open_critical": 7, "open_total": 34},
    "yahoo": {"platform": "HackerOne", "open_critical": 9, "open_total": 55},
    "linkedin": {"platform": "HackerOne", "open_critical": 3, "open_total": 28},
    "intel": {"platform": "HackerOne", "open_critical": 2, "open_total": 33},
    "nvidia": {"platform": "HackerOne", "open_critical": 1, "open_total": 12},
    "samsung": {"platform": "HackerOne", "open_critical": 5, "open_total": 41},
    "spotify": {"platform": "HackerOne", "open_critical": 1, "open_total": 9},
    "verizon": {"platform": "Bugcrowd", "open_critical": 3, "open_total": 16},
    "at&t": {"platform": "Bugcrowd", "open_critical": 4, "open_total": 21},
    "att": {"platform": "Bugcrowd", "open_critical": 4, "open_total": 21},
}

# ---------------------------------------------------------------------------
# Suspicious domain patterns that contribute to domain risk score
# ---------------------------------------------------------------------------
_SUSPICIOUS_TLD_PATTERNS = [
    r"\.xyz$", r"\.top$", r"\.click$", r"\.loan$", r"\.download$",
    r"\.stream$", r"\.gdn$", r"\.win$", r"\.bid$", r"\.trade$",
]
_SUSPICIOUS_KEYWORD_PATTERNS = [
    r"secure[\-_]?login", r"account[\-_]?verify", r"update[\-_]?info",
    r"signin[\-_]?", r"verify[\-_]?account", r"confirm[\-_]?payment",
]


# ===========================================================================
# LangChain @tool definitions
# Each function is decorated with @tool so the LLM can invoke it by name.
# ===========================================================================

@tool
def check_breach_database(vendor_name: str) -> str:
    """
    Check a simulated breach intelligence database for the given vendor.
    Returns known breach incidents or a clean confirmation.
    Input: vendor_name (str) — the company/vendor name to look up.
    """
    # Normalize the name for lookup (lowercase, strip common suffixes)
    key = vendor_name.lower().strip()
    for suffix in [" inc", " corp", " ltd", " llc", " co", ".", ","]:
        key = key.rstrip(suffix)

    breaches = _BREACH_DB.get(key, [])

    if not breaches:
        return f"NO_BREACH_FOUND: No known breach history found for '{vendor_name}' in the database."

    lines = [f"BREACH_FOUND: {len(breaches)} known breach(es) for '{vendor_name}':"]
    for b in breaches:
        lines.append(
            f"  - Date: {b['date']} | Records: {b['records_affected']:,} | "
            f"Data: {', '.join(b['data_types'])} | {b['description']}"
        )
    return "\n".join(lines)


@tool
def check_bug_bounty_exposure(vendor_name: str) -> str:
    """
    Check whether the vendor has an active bug bounty program on HackerOne or Bugcrowd,
    and return simulated open/critical vulnerability counts.
    Input: vendor_name (str) — the company/vendor name to look up.
    """
    key = vendor_name.lower().strip()
    for suffix in [" inc", " corp", " ltd", " llc", " co", ".", ","]:
        key = key.rstrip(suffix)

    # Direct match first
    entry = _BUG_BOUNTY_REGISTRY.get(key)

    # Fuzzy match: check if the key is a substring of any registry key or vice versa
    if not entry:
        for reg_key, val in _BUG_BOUNTY_REGISTRY.items():
            if key in reg_key or reg_key in key:
                entry = val
                break

    if not entry:
        return (
            f"NO_PROGRAM_FOUND: No bug bounty program found for '{vendor_name}' "
            "on HackerOne or Bugcrowd. This may indicate limited public security disclosure."
        )

    return (
        f"BUG_BOUNTY_FOUND: '{vendor_name}' has a program on {entry['platform']}. "
        f"Open vulnerabilities: {entry['open_total']} total, "
        f"{entry['open_critical']} critical/high severity."
    )


@tool
def analyze_domain_risk(website: str) -> str:
    """
    Perform a WHOIS-like domain age and pattern analysis to assess domain risk.
    Evaluates TLD, domain length, suspicious keywords, and URL structure.
    Input: website (str) — the vendor's website URL (e.g., https://example.com).
    """
    try:
        parsed = urlparse(website if "://" in website else f"https://{website}")
        domain = parsed.netloc or parsed.path
        domain = domain.lower().strip().lstrip("www.")
    except Exception as e:
        return f"DOMAIN_ANALYSIS_ERROR: Could not parse domain from '{website}': {e}"

    risk_flags: list[str] = []
    risk_score = 0

    # Check for suspicious TLDs
    for pattern in _SUSPICIOUS_TLD_PATTERNS:
        if re.search(pattern, domain):
            risk_flags.append(f"Suspicious TLD detected: matches pattern '{pattern}'")
            risk_score += 15

    # Check for suspicious keywords in domain
    for pattern in _SUSPICIOUS_KEYWORD_PATTERNS:
        if re.search(pattern, domain):
            risk_flags.append(f"Suspicious keyword pattern in domain: '{pattern}'")
            risk_score += 20

    # Very short or very long domains are suspicious
    domain_name = domain.split(".")[0]
    if len(domain_name) < 3:
        risk_flags.append(f"Very short domain name ('{domain_name}') — possible squatting")
        risk_score += 10
    elif len(domain_name) > 30:
        risk_flags.append(f"Unusually long domain name ({len(domain_name)} chars) — possible obfuscation")
        risk_score += 10

    # Excessive hyphens
    if domain_name.count("-") >= 3:
        risk_flags.append(f"Many hyphens in domain ({domain_name.count('-')}) — common in phishing domains")
        risk_score += 12

    # IP address instead of domain
    ip_pattern = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
    if ip_pattern.match(domain):
        risk_flags.append("Website uses raw IP address instead of domain name")
        risk_score += 25

    # Numeric-heavy domain
    digit_ratio = sum(c.isdigit() for c in domain_name) / max(len(domain_name), 1)
    if digit_ratio > 0.4:
        risk_flags.append(f"High digit ratio in domain ({digit_ratio:.0%}) — possible DGA domain")
        risk_score += 10

    # Simulate domain age risk: well-known TLDs are generally older/more trusted
    trusted_tlds = {".com", ".org", ".net", ".edu", ".gov", ".co.uk", ".de", ".fr", ".jp"}
    if not any(domain.endswith(tld) for tld in trusted_tlds):
        risk_flags.append("Non-standard TLD — domain may be newer or less established")
        risk_score += 5

    # Build result
    risk_level = "LOW" if risk_score < 15 else ("MEDIUM" if risk_score < 35 else "HIGH")
    result_lines = [
        f"DOMAIN_ANALYSIS: '{domain}' | Risk Score: {risk_score}/100 | Level: {risk_level}"
    ]
    if risk_flags:
        result_lines.append("Risk flags:")
        for flag in risk_flags:
            result_lines.append(f"  - {flag}")
    else:
        result_lines.append("No domain risk flags detected.")

    return "\n".join(result_lines)


@tool
def check_ssl_certificate(website: str) -> str:
    """
    Verify the SSL/TLS certificate for the vendor's website.
    Checks HTTPS availability, certificate validity, expiry, and issuer.
    Input: website (str) — the vendor's website URL.
    """
    # Normalise URL
    if not website.startswith("http"):
        website = f"https://{website}"
    if website.startswith("http://"):
        website = website.replace("http://", "https://", 1)

    try:
        parsed = urlparse(website)
        hostname = parsed.netloc or parsed.path
        hostname = hostname.split(":")[0]  # strip port if present
    except Exception as e:
        return f"SSL_CHECK_ERROR: Could not parse hostname from '{website}': {e}"

    # --- Live HTTPS request (requests library handles cert validation) ---
    try:
        response = requests.get(
            website,
            timeout=10,
            allow_redirects=True,
            headers={"User-Agent": "VendorGuard-SecurityAudit/1.0"},
        )
        https_reachable = True
        status_code = response.status_code
        final_url = response.url
    except requests.exceptions.SSLError as e:
        return (
            f"SSL_INVALID: '{hostname}' has an INVALID or SELF-SIGNED certificate. "
            f"SSL error: {e}"
        )
    except requests.exceptions.ConnectionError as e:
        return f"SSL_UNREACHABLE: Could not connect to '{hostname}' over HTTPS. Error: {e}"
    except requests.exceptions.Timeout:
        return f"SSL_TIMEOUT: Connection to '{hostname}' timed out after 10 seconds."
    except Exception as e:
        return f"SSL_CHECK_ERROR: Unexpected error checking '{hostname}': {e}"

    # --- Low-level cert inspection to extract expiry and issuer ---
    cert_info: dict[str, Any] = {}
    days_until_expiry: int | None = None
    try:
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(
            socket.create_connection((hostname, 443), timeout=10),
            server_hostname=hostname,
        ) as ssock:
            cert = ssock.getpeercert()
            cert_info = cert

        # Parse expiry date
        expiry_str = cert.get("notAfter", "")
        if expiry_str:
            expiry_dt = datetime.datetime.strptime(expiry_str, "%b %d %H:%M:%S %Y %Z")
            days_until_expiry = (expiry_dt - datetime.datetime.utcnow()).days

        issuer_dict = dict(x[0] for x in cert.get("issuer", []))
        issuer = issuer_dict.get("organizationName", "Unknown")
        subject_dict = dict(x[0] for x in cert.get("subject", []))
        common_name = subject_dict.get("commonName", hostname)

    except Exception:
        # If low-level inspection fails but requests succeeded, the cert is at
        # least valid enough for a standard TLS handshake — report partial info
        issuer = "Unknown (cert inspection failed)"
        common_name = hostname
        days_until_expiry = None

    # Build result
    lines = [f"SSL_VALID: '{hostname}' has a valid HTTPS certificate."]
    lines.append(f"  Common Name   : {common_name}")
    lines.append(f"  Issuer        : {issuer}")
    if days_until_expiry is not None:
        expiry_status = (
            "EXPIRING SOON (<30 days)" if days_until_expiry < 30
            else ("EXPIRED" if days_until_expiry < 0 else "OK")
        )
        lines.append(f"  Days to Expiry: {days_until_expiry} ({expiry_status})")
        if days_until_expiry < 0:
            lines.append("  WARNING: Certificate is EXPIRED.")
        elif days_until_expiry < 30:
            lines.append("  WARNING: Certificate expires very soon.")
    lines.append(f"  HTTP Status   : {status_code}")
    if final_url != website:
        lines.append(f"  Redirected to : {final_url}")

    return "\n".join(lines)


# ===========================================================================
# ThreatIntelAgent
# ===========================================================================

class ThreatIntelAgent:
    """
    Agent B in the VendorGuard pipeline.

    Uses a LangChain tool-calling agent backed by Groq's llama-3.3-70b-versatile
    to orchestrate four threat intelligence checks and return a structured result.
    """

    # LangChain tools available to the agent
    _TOOLS = [
        check_breach_database,
        check_bug_bounty_exposure,
        analyze_domain_risk,
        check_ssl_certificate,
    ]

    # System prompt instructing the LLM how to use the tools and format output
    _SYSTEM_PROMPT = """You are a threat intelligence analyst for VendorGuard, a vendor security \
assessment platform. Your job is to investigate a vendor by running exactly these four checks \
in order:

1. check_breach_database — look up the vendor name for known data breaches
2. check_bug_bounty_exposure — check for active bug bounty programs and open vulnerability counts
3. analyze_domain_risk — evaluate the vendor's website domain for risk indicators
4. check_ssl_certificate — verify the HTTPS/TLS certificate on the vendor's website

After running ALL four tools, summarise your findings clearly. You MUST run all four tools \
before producing a final answer. Do not skip any tool."""

    def __init__(self) -> None:
        self._llm: ChatGroq | None = None
        self._agent = None

    def _get_agent(self):
        """Lazy-init the LangGraph ReAct agent."""
        if self._agent is not None:
            return self._agent
        self._llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0,
            groq_api_key=os.getenv("GROQ_API_KEY"),
        )
        self._agent = create_react_agent(
            self._llm,
            self._TOOLS,
            prompt=SystemMessage(content=self._SYSTEM_PROMPT),
        )
        return self._agent

    # ------------------------------------------------------------------
    # Internal helpers for parsing raw tool outputs
    # ------------------------------------------------------------------

    def _parse_breach_history(self, tool_outputs: dict[str, str]) -> list[dict[str, Any]]:
        """Extract structured breach records from the breach-check tool output."""
        raw = tool_outputs.get("breach", "")
        if "NO_BREACH_FOUND" in raw or not raw:
            return []

        breaches: list[dict[str, Any]] = []
        for line in raw.splitlines():
            line = line.strip()
            if line.startswith("- Date:"):
                parts = line.lstrip("- ").split(" | ")
                record: dict[str, Any] = {}
                for part in parts:
                    if part.startswith("Date:"):
                        record["date"] = part.replace("Date:", "").strip()
                    elif part.startswith("Records:"):
                        try:
                            record["records_affected"] = int(
                                part.replace("Records:", "").strip().replace(",", "")
                            )
                        except ValueError:
                            record["records_affected"] = 0
                    elif part.startswith("Data:"):
                        record["data_types"] = [
                            d.strip() for d in part.replace("Data:", "").split(",")
                        ]
                    else:
                        record["description"] = part.strip()
                if record:
                    breaches.append(record)
        return breaches

    def _parse_bug_bounty(self, tool_outputs: dict[str, str]) -> dict[str, Any]:
        """Extract structured bug bounty info from the bounty-check tool output."""
        raw = tool_outputs.get("bounty", "")
        if "NO_PROGRAM_FOUND" in raw or not raw:
            return {"platform": None, "open_count": 0, "critical_count": 0}

        platform = None
        open_count = 0
        critical_count = 0

        for plat in ["HackerOne", "Bugcrowd"]:
            if plat in raw:
                platform = plat
                break

        # Extract counts with regex
        total_match = re.search(r"(\d+)\s+total", raw)
        crit_match = re.search(r"(\d+)\s+critical", raw, re.IGNORECASE)
        if total_match:
            open_count = int(total_match.group(1))
        if crit_match:
            critical_count = int(crit_match.group(1))

        return {"platform": platform, "open_count": open_count, "critical_count": critical_count}

    def _compute_threat_score(
        self,
        breach_history: list[dict[str, Any]],
        bug_bounty: dict[str, Any],
        domain_raw: str,
        ssl_raw: str,
    ) -> int:
        """
        Derive a 0-50 threat score contribution from the four checks.

        Scoring breakdown:
          - Breach history   : up to 25 points (based on number and severity)
          - Bug bounty open  : up to 10 points (critical count drives this)
          - Domain risk      : up to 10 points (extracted from domain analysis)
          - SSL issues       : up to 5  points (invalid/expired certs)
        """
        score = 0

        # Breach scoring: 8 points per breach, capped at 25
        score += min(len(breach_history) * 8, 25)

        # Bug bounty: 2 pts per critical finding, capped at 10
        score += min(bug_bounty.get("critical_count", 0) * 2, 10)

        # Domain: try to extract the numeric score from the tool output
        domain_score_match = re.search(r"Risk Score:\s*(\d+)", domain_raw)
        if domain_score_match:
            raw_domain_score = int(domain_score_match.group(1))
            # Scale 0-100 domain score to 0-10 range
            score += min(int(raw_domain_score / 10), 10)

        # SSL: 5 points for invalid/expired cert, 2 for expiring soon
        if "SSL_INVALID" in ssl_raw or "EXPIRED" in ssl_raw:
            score += 5
        elif "EXPIRING SOON" in ssl_raw:
            score += 2
        if "SSL_UNREACHABLE" in ssl_raw or "SSL_TIMEOUT" in ssl_raw:
            score += 3

        return min(score, 50)  # cap at 50

    def _extract_threat_findings(
        self,
        breach_history: list[dict[str, Any]],
        bug_bounty: dict[str, Any],
        domain_raw: str,
        ssl_raw: str,
        vendor_name: str,
    ) -> list[str]:
        """Build a human-readable list of threat findings."""
        findings: list[str] = []

        if breach_history:
            findings.append(
                f"{vendor_name} has {len(breach_history)} known data breach(es) on record."
            )
            most_recent = sorted(breach_history, key=lambda x: x.get("date", ""), reverse=True)
            if most_recent:
                b = most_recent[0]
                findings.append(
                    f"Most recent breach ({b.get('date', 'unknown')}): "
                    f"{b.get('records_affected', 0):,} records exposed "
                    f"({', '.join(b.get('data_types', []))})."
                )
        else:
            findings.append(f"No known breach history found for {vendor_name}.")

        if bug_bounty.get("platform"):
            findings.append(
                f"{vendor_name} has an active bug bounty program on {bug_bounty['platform']} "
                f"with {bug_bounty['open_count']} open reports "
                f"({bug_bounty['critical_count']} critical/high)."
            )
            if bug_bounty.get("critical_count", 0) >= 5:
                findings.append(
                    "High number of open critical findings indicates unresolved security exposure."
                )
        else:
            findings.append(
                f"{vendor_name} has no known public bug bounty program — "
                "limited external security research visibility."
            )

        # Surface notable domain flags
        if "MEDIUM" in domain_raw or "HIGH" in domain_raw:
            findings.append(f"Domain risk analysis flagged concerns: see details in domain report.")
        else:
            findings.append("Domain risk analysis found no significant red flags.")

        # Surface SSL status
        if "SSL_VALID" in ssl_raw:
            findings.append("SSL/TLS certificate is valid and HTTPS is operational.")
            if "EXPIRING SOON" in ssl_raw:
                findings.append("WARNING: SSL certificate is expiring within 30 days.")
        elif "SSL_INVALID" in ssl_raw:
            findings.append("CRITICAL: SSL certificate is invalid or self-signed.")
        elif "SSL_UNREACHABLE" in ssl_raw:
            findings.append("WARNING: Website is unreachable over HTTPS.")
        else:
            findings.append(f"SSL check note: {ssl_raw[:120]}")

        return findings

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def analyze(self, vendor_name: str, website: str) -> dict[str, Any]:
        """
        Run all threat intelligence checks for the given vendor.

        Args:
            vendor_name: Human-readable vendor/company name (e.g. "Adobe Inc.")
            website:     The vendor's primary website URL (e.g. "https://adobe.com")

        Returns:
            A dict with the following keys:
              - threat_findings          (list[str])  Human-readable threat findings
              - breach_history           (list[dict]) Structured breach records
              - bug_bounty_exposure      (dict)       Platform and open vulnerability count
              - threat_score_contribution (int)       0-50 risk score contribution
              - requires_human_review    (bool)       True if score > 30 or breaches exist
        """
        # Collect raw outputs from each tool for post-processing.
        # We run the tools directly (bypassing the LLM for deterministic mock data)
        # and also invoke the agent for its narrative summary.
        raw_outputs: dict[str, str] = {}

        try:
            raw_outputs["breach"] = check_breach_database.invoke({"vendor_name": vendor_name})
        except Exception as exc:
            raw_outputs["breach"] = f"TOOL_ERROR: {exc}"

        try:
            raw_outputs["bounty"] = check_bug_bounty_exposure.invoke({"vendor_name": vendor_name})
        except Exception as exc:
            raw_outputs["bounty"] = f"TOOL_ERROR: {exc}"

        try:
            raw_outputs["domain"] = analyze_domain_risk.invoke({"website": website})
        except Exception as exc:
            raw_outputs["domain"] = f"TOOL_ERROR: {exc}"

        try:
            raw_outputs["ssl"] = check_ssl_certificate.invoke({"website": website})
        except Exception as exc:
            raw_outputs["ssl"] = f"TOOL_ERROR: {exc}"

        # Parse structured data from raw tool outputs
        breach_history = self._parse_breach_history(raw_outputs)
        bug_bounty_exposure = self._parse_bug_bounty(raw_outputs)
        threat_score = self._compute_threat_score(
            breach_history,
            bug_bounty_exposure,
            raw_outputs.get("domain", ""),
            raw_outputs.get("ssl", ""),
        )
        threat_findings = self._extract_threat_findings(
            breach_history,
            bug_bounty_exposure,
            raw_outputs.get("domain", ""),
            raw_outputs.get("ssl", ""),
            vendor_name,
        )

        # Also run the LLM agent to enrich findings with any additional insight
        try:
            agent_input = (
                f"Analyse the threat intelligence for vendor '{vendor_name}' "
                f"with website '{website}'. Run all four checks."
            )
            agent = self._get_agent()
            agent_result = agent.invoke({"messages": [("human", agent_input)]})
            llm_summary = agent_result["messages"][-1].content
            if llm_summary and len(llm_summary) > 20:
                threat_findings.append(f"[LLM Analysis] {llm_summary.strip()}")
        except Exception as exc:
            # LLM enrichment is best-effort; don't fail the whole analysis
            threat_findings.append(f"[LLM Analysis unavailable: {exc}]")

        requires_human_review = threat_score > 30 or len(breach_history) > 0

        return {
            "threat_findings": threat_findings,
            "breach_history": breach_history,
            "bug_bounty_exposure": {
                "platform": bug_bounty_exposure.get("platform"),
                "open_count": bug_bounty_exposure.get("open_count", 0),
            },
            "threat_score_contribution": threat_score,
            "requires_human_review": requires_human_review,
        }


# ---------------------------------------------------------------------------
# Quick smoke-test (run this file directly to verify wiring)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json

    agent = ThreatIntelAgent()

    test_cases = [
        ("Adobe Inc.", "https://adobe.com"),
        ("Acme Widgets", "https://acmewidgets.com"),
        ("Yahoo", "https://yahoo.com"),
    ]

    for vendor, site in test_cases:
        print(f"\n{'='*60}")
        print(f"Analysing: {vendor} ({site})")
        print("=" * 60)
        result = agent.analyze(vendor, site)
        print(json.dumps(result, indent=2, default=str))
