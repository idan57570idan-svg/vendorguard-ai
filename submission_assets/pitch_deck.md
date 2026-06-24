# VendorGuard AI — Pitch Deck
# UiPath AgentHack 2026 | Track 1: UiPath Maestro Case

---

## SLIDE 1 — TITLE

```
VendorGuard AI
Automated Vendor Security Reviews
Powered by LangGraph + UiPath Maestro Case

Built with Claude Code (UiPath for Coding Agents)
AgentHack 2026 | Track 1: UiPath Maestro Case
```

---

## SLIDE 2 — THE PROBLEM

**The Vendor Security Review Bottleneck**

Every enterprise with SOC2, ISO27001, HIPAA, or PCI-DSS compliance requirements must
vet every third-party vendor before onboarding.

**Today's process:**
- Analyst opens vendor website manually
- Checks for compliance certs (SOC2? ISO27001? FedRAMP?)
- Googles breach history, HackerOne listings
- Reviews SSL cert, hosting region for data residency
- Fills a spreadsheet row-by-row
- Escalates to security team if risky

**The cost:**
| Metric | Value |
|--------|-------|
| Time per vendor | 2–4 hours |
| Vendors per quarter | ~50 |
| Analyst cost | $80/hour |
| **Quarterly cost** | **$8,000–$16,000** |
| **Annual cost** | **$32,000–$64,000** |

And that's before accounting for missed risks, delayed procurement, and compliance gaps.

---

## SLIDE 3 — THE SOLUTION

**VendorGuard AI**

> Drop a vendor name + website. Get a security score, compliance report,
> and a routing decision — in under 2 seconds.

**How it works in one sentence:**
Two parallel LangGraph AI agents analyze the vendor's public surface,
score the risk, and route the outcome through UiPath Maestro Case —
auto-approving safe vendors, escalating risky ones to a human analyst.

**Key outcomes:**
- 100x faster than manual review
- Consistent, auditable results (no analyst-to-analyst variance)
- Zero missed compliance gaps — 30+ signals checked every time
- Full UiPath Maestro Case integration (intake → AI → approve/escalate)

---

## SLIDE 4 — ARCHITECTURE

```
[Procurement Request]
        |
[UiPath Maestro Case — Intake]
        |
        | API Workflow: POST /analyze-vendor
        v
[FastAPI Orchestrator :8000]
       /                    \
  [Agent A]              [Agent B]
  SaaS Auditor           Threat Intel
  (LangGraph)            (LangGraph)
       |                    |
  scrape website        breach DB check
  detect SOC2/ISO       bug bounty lookup
  hosting regions       domain risk score
  score 0-50            SSL/TLS live check
       |                    |
       \                    /
    [Risk Score: 1-100]
         |
    score >= 70?
   /              \
[AUTO-APPROVE]  [HUMAN REVIEW]
Robot syncs     Security Analyst
to ERP          48h SLA Maestro task
```

**Tech stack:**
- Python 3.14 + FastAPI 0.138 + Pydantic v2
- LangGraph 1.x (prebuilt React agents)
- Groq API (llama-3.3-70b-versatile) — free tier, 6K tokens/min
- BeautifulSoup4 + requests (web scraping)
- Offline mock mode — 8 enterprise vendor profiles for instant demos

---

## SLIDE 5 — UIPATH PLATFORM USAGE

| UiPath Component | How VendorGuard Uses It |
|------------------|------------------------|
| **Maestro Case** | 5-stage case lifecycle (intake → AI → auto_approved / human_review → approved / rejected) |
| **API Workflows** | Calls POST /analyze-vendor, maps response fields to case |
| **Human-in-the-Loop** | `human_review` stage: task form with full AI report, 48h SLA |
| **Robots** | Auto-approval stage: syncs decision to ERP procurement module |
| **Notifications** | Email templates for all 5 stage transitions |
| **Agent Builder** | VendorGuard wrapped as a native UiPath agent for orchestration |
| **Coding Agents** | Entire backend built with Claude Code (UiPath for Coding Agents) |

---

## SLIDE 6 — LIVE DEMO

**Demo flow (5 minutes):**

1. `python evaluate_vendor.py Adobe https://adobe.com`
   → Score 71 | 2013 breach flagged | → HUMAN REVIEW

2. `python evaluate_vendor.py Microsoft https://microsoft.com`
   → Score 96 | 7 certs confirmed | → AUTO-APPROVED

3. API call via Swagger UI (`localhost:8000/docs`)
   → Notion: score 82, returns in <200ms

4. UiPath Maestro Case — case transitions in UI

5. Claude Code terminal — coding agent in action (bonus)

---

## SLIDE 7 — ROI & MARKET SIZE

**ROI per enterprise customer:**
- Save 100–200 analyst hours/quarter
- $8,000–$16,000 saved per quarter = **$32,000–$64,000/year per org**
- Reduced breach risk exposure (avg. breach cost: $4.45M — IBM 2024)

**Market size:**
- Every Fortune 500 company has a vendor security review process
- 500,000+ companies with SOC2/ISO27001 requirements globally
- TAM: $2B+ (vendor risk management software market, 2024)

**Competitive advantage:**
- Existing solutions (BitSight, SecurityScorecard) cost $50K+/year
- VendorGuard: open-source core, UiPath-native, instant deployment

---

## SLIDE 8 — ACCOMPLISHMENTS

- 9/9 automated tests passing on Python 3.14
- Offline mock mode — 8 enterprise vendor profiles — zero setup required
- LangGraph 1.x migration (replaced deprecated AgentExecutor)
- Full UiPath Maestro Case workflow JSON ready to import
- CLI dashboard with ANSI color output + JSON export mode
- Built entirely with Claude Code (UiPath for Coding Agents) — eligible for coding agent bonus

---

## SLIDE 9 — FUTURE ROADMAP

**Short term (Q3 2026):**
- Real-time BreachDirectory / HaveIBeenPwned API integration
- CISA Known Exploited Vulnerabilities (KEV) feed check
- PDF export of audit report for compliance archives

**Medium term (Q4 2026):**
- Vendor re-check scheduler (quarterly auto-refresh via Maestro)
- Slack/Teams notification integration for analyst escalations
- Multi-vendor batch processing (CSV upload → parallel cases)

**Long term (2027):**
- Vendor risk score trend tracking over time
- ML model trained on known breach patterns
- Native UiPath Marketplace listing

---

## SLIDE 10 — BUILT WITH

```
Claude Code (UiPath for Coding Agents)
+ Python 3.14 + FastAPI + LangGraph + Groq
+ UiPath Maestro Case + API Workflows + Robots
= VendorGuard AI
```

**GitHub:** [repository URL]
**Demo video:** [YouTube URL]
**Track:** Track 1 — UiPath Maestro Case
**Hackathon:** UiPath AgentHack 2026 | $50,000 prize pool
