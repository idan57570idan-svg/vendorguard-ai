#!/usr/bin/env python3
# MIT License -- Copyright (c) 2026 VendorGuard AI
"""
VendorGuard AI -- Command-Line Vendor Evaluator
================================================
Run a full security assessment without lifting the FastAPI server.

Usage:
    python evaluate_vendor.py <vendor_name> <website_url>

Examples:
    python evaluate_vendor.py Microsoft https://microsoft.com
    python evaluate_vendor.py Notion https://notion.so
    python evaluate_vendor.py "Acme Corp" https://acmecorp.io
"""

import os
import sys
import json
import argparse
import textwrap
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# ANSI colour helpers (no external deps, ASCII-safe symbols)
# ---------------------------------------------------------------------------

RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"

RED     = "\033[31m"
GREEN   = "\033[32m"
YELLOW  = "\033[33m"
BLUE    = "\033[34m"
MAGENTA = "\033[35m"
CYAN    = "\033[36m"
WHITE   = "\033[37m"


def c(text: str, *codes: str) -> str:
    return "".join(codes) + text + RESET


def header(text: str) -> str:
    width = 64
    bar = "-" * width
    return (
        f"\n{c(bar, CYAN)}\n"
        f"  {c(text, BOLD, CYAN)}\n"
        f"{c(bar, CYAN)}"
    )


def score_bar(score: int, width: int = 40) -> str:
    filled = int(round(score / 100 * width))
    empty  = width - filled
    if score >= 75:
        colour = GREEN
        label  = "TRUSTED"
    elif score >= 50:
        colour = YELLOW
        label  = "MODERATE"
    else:
        colour = RED
        label  = "HIGH RISK"
    bar = c("#" * filled, colour) + c("." * empty, DIM) + f"  {c(str(score), BOLD, colour)}/100"
    return f"{bar}  {c(f'[{label}]', BOLD, colour)}"


def bullet(text: str, colour: str = WHITE) -> str:
    return f"  {c('*', colour, BOLD)} {c(text, colour)}"


def flag_icon(value: bool) -> str:
    if value:
        return c("[!] ESCALATE TO HUMAN REVIEW", BOLD, RED)
    return c("[OK] AUTO-APPROVED", BOLD, GREEN)


# ---------------------------------------------------------------------------
# Core assessment logic (reuses the same backend code as the API)
# ---------------------------------------------------------------------------

def run_assessment(vendor_name: str, website: str) -> dict:
    """Run the full VendorGuard assessment and return the combined result dict."""
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    mock_mode = not groq_key or groq_key.lower() in (
        "placeholder", "your_groq_api_key_here", "none", "false"
    )

    if mock_mode:
        print(c("\n  [i] No GROQ_API_KEY detected -- running in MOCK mode (demo data)", DIM, YELLOW))
        from api.main import _generate_mock_response
        saas_result, threat_result = _generate_mock_response(vendor_name, website)
        mode = "mock"
    else:
        print(c("\n  [>] LIVE mode -- running LangGraph agents...", CYAN))
        try:
            from agents.saas_auditor import SaaSAuditorAgent
            from agents.threat_intel import ThreatIntelAgent

            print(c("  -> Agent A (SaaS Auditor) scraping website...", DIM))
            saas_result = SaaSAuditorAgent().analyze(vendor_name=vendor_name, website=website)

            print(c("  -> Agent B (Threat Intel) running checks...", DIM))
            threat_result = ThreatIntelAgent().analyze(vendor_name=vendor_name, website=website)
            mode = "live"
        except Exception as exc:
            print(c(f"\n  [!] Agent error ({exc}) -- falling back to mock", YELLOW))
            from api.main import _generate_mock_response
            saas_result, threat_result = _generate_mock_response(vendor_name, website)
            mode = "mock-fallback"

    raw_score = (
        saas_result.get("security_score_contribution", 0)
        + threat_result.get("threat_score_contribution", 0)
    )
    security_score = max(1, min(100, raw_score))

    key_findings = (
        saas_result.get("findings", [])
        + threat_result.get("threat_findings", threat_result.get("findings", []))
    )

    requires_review = (
        security_score < 50
        or threat_result.get("requires_human_review", False)
        or any(
            f.lower().startswith("critical") or "breach detected" in f.lower()
            for f in key_findings
        )
    )

    return {
        "vendor_name": vendor_name,
        "website": website,
        "security_score": security_score,
        "key_findings": key_findings,
        "requires_human_review": requires_review,
        "details": {
            "saas_audit": saas_result,
            "threat_intel": threat_result,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
    }


# ---------------------------------------------------------------------------
# Terminal dashboard renderer
# ---------------------------------------------------------------------------

def render_dashboard(result: dict) -> None:
    vendor  = result["vendor_name"]
    website = result["website"]
    score   = result["security_score"]
    review  = result["requires_human_review"]
    mode    = result.get("mode", "unknown")
    ts      = result["timestamp"]
    details = result["details"]

    saas   = details.get("saas_audit", {})
    threat = details.get("threat_intel", {})

    certs   = saas.get("compliance_certs", [])
    regions = saas.get("hosting_regions", [])
    breach  = threat.get("breach_history", [])

    # Title
    print(header("VendorGuard AI  *  Enterprise Vendor Security Assessment"))
    print(f"\n  {c('Vendor  :', DIM)}  {c(vendor, BOLD, WHITE)}")
    print(f"  {c('Website :', DIM)}  {c(website, CYAN)}")
    print(f"  {c('Run at  :', DIM)}  {c(ts[:19].replace('T', ' ') + ' UTC', DIM)}")
    print(f"  {c('Mode    :', DIM)}  {c(mode.upper(), MAGENTA)}")

    # Risk score
    print(header("Risk Score"))
    print(f"\n  {score_bar(score)}\n")

    # UiPath Maestro Case decision
    print(header("UiPath Maestro Case Decision"))
    print(f"\n  {flag_icon(review)}\n")
    if review:
        print(bullet("Case will be routed to Security Analyst queue", YELLOW))
        print(bullet("SLA: 48 hours for human review and sign-off", YELLOW))
        print(bullet("Requestor will be notified of escalation via Maestro", YELLOW))
    else:
        print(bullet("Vendor approved automatically -- no human review required", GREEN))
        print(bullet("UiPath robot will sync approval to ERP procurement module", GREEN))
        print(bullet("Requestor notified via automated Maestro email workflow", GREEN))

    # Compliance certifications
    print(header("Compliance Certifications"))
    if certs:
        for cert in certs:
            colour = GREEN if cert in ("SOC2", "ISO27001", "FedRAMP") else CYAN
            print(bullet(cert, colour))
    else:
        print(bullet("No compliance certs detected -- request vendor documentation", YELLOW))

    # Hosting regions
    print(header("Hosting & Infrastructure"))
    if regions:
        for region in regions:
            print(bullet(region, CYAN))
    else:
        print(bullet("Hosting region unknown -- verify data residency requirements", YELLOW))

    # Breach history
    print(header("Breach History"))
    if breach:
        for b in breach:
            date = b.get("date", "unknown")
            records = f"{b.get('records_affected', 0):,}"
            print(bullet(f"{date} -- {records} records affected", RED))
    else:
        print(bullet("No breach history found in monitored databases", GREEN))

    # Key findings
    print(header("Key Findings"))
    findings = result.get("key_findings", [])
    for f in findings[:10]:
        is_warn = any(w in f.lower() for w in ("warning", "critical", "breach", "invalid", "high"))
        colour  = RED if is_warn else (
            GREEN if any(w in f.lower() for w in ("valid", "no breach", "certified", "soc2", "approved"))
            else WHITE
        )
        wrapped = textwrap.wrap(f, width=56)
        for i, line in enumerate(wrapped):
            prefix = "*" if i == 0 else " "
            print(f"  {c(prefix, colour, BOLD)} {c(line, colour)}")

    if len(findings) > 10:
        print(c(f"\n  ... and {len(findings) - 10} more findings in full JSON output.", DIM))

    # UiPath integration hint
    print(header("UiPath Integration"))
    next_step = "Assign to security_team queue" if review else "Sync to ERP via API Workflow"
    stage = "human_review" if review else "auto_approved"
    print(f"""
  {c('POST', BOLD, BLUE)} http://localhost:8000/analyze-vendor
  {c('Body:', DIM)} {{"vendor_name": "{vendor}", "website": "{website}"}}

  {c('-> Maestro Case Stage:', DIM)}  {stage}
  {c('-> Workflow file:', DIM)}       uipath/maestro_case_workflow.json
  {c('-> Next step:', DIM)}           {next_step}
""")

    # Footer
    bar = "-" * 64
    print(c(bar, DIM))
    print(f"  {c('Built with Claude Code * UiPath for Coding Agents * AgentHack 2026', DIM)}")
    print(c(bar, DIM))
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="VendorGuard AI -- CLI vendor security evaluator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python evaluate_vendor.py Microsoft https://microsoft.com
              python evaluate_vendor.py Notion https://notion.so
              python evaluate_vendor.py "Acme Corp" https://acmecorp.io
              python evaluate_vendor.py --json Stripe https://stripe.com
        """),
    )
    parser.add_argument("vendor_name", help="Name of the vendor to assess")
    parser.add_argument("website",     help="Vendor's primary website URL (https://...)")
    parser.add_argument(
        "--json", action="store_true",
        help="Output raw JSON instead of the dashboard (useful for piping to UiPath)",
    )
    args = parser.parse_args()

    result = run_assessment(args.vendor_name, args.website)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        render_dashboard(result)


if __name__ == "__main__":
    main()
