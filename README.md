# VendorGuard AI

**Automated vendor security analysis powered by AI agents — built for UiPath Maestro Case (Track 1)**

[![UiPath AgentHack](https://img.shields.io/badge/UiPath-AgentHack%202026-0052CC)](https://uipath.com)
[![Track](https://img.shields.io/badge/Track-Maestro%20Case-green)](https://devpost.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Built with Claude Code](https://img.shields.io/badge/Built%20with-Claude%20Code-orange)](https://claude.ai/code)

## What It Does

VendorGuard AI automates the vendor security review process that typically takes procurement teams days of manual work. When a company wants to onboard a new SaaS vendor, VendorGuard:

1. **Audits the vendor's public security posture** — scrapes their website for compliance certifications (SOC2, ISO27001, PCI-DSS, GDPR, HIPAA), hosting regions, security documentation, and trust signals.
2. **Checks threat intelligence** — looks up breach history, bug bounty exposure, domain risk indicators, and SSL certificate validity.
3. **Scores the vendor 1–100** and flags high-risk vendors for **human review** inside UiPath Maestro Case.

## Business Problem

Enterprise procurement teams review dozens of SaaS vendors per quarter. Each review requires:
- Manual website auditing (30–90 minutes per vendor)
- Cross-referencing compliance certifications
- Checking breach databases and bug bounty platforms
- Writing a security summary for the procurement committee

VendorGuard automates all of this in under 60 seconds, with human escalation baked in via UiPath Maestro Case for high-risk vendors.

## Architecture

```
UiPath Maestro Case
       │
       ▼
┌─────────────────────────────────────────┐
│           VendorGuard AI API            │
│        POST /analyze-vendor             │
│                                         │
│  ┌──────────────┐  ┌──────────────────┐ │
│  │ Agent A      │  │ Agent B          │ │
│  │ SaaS Auditor │  │ Threat Intel     │ │
│  │              │  │                  │ │
│  │ • Web scrape │  │ • Breach DB      │ │
│  │ • Compliance │  │ • Bug bounty     │ │
│  │ • Hosting    │  │ • Domain risk    │ │
│  │ • Trust sig. │  │ • SSL/TLS check  │ │
│  └──────────────┘  └──────────────────┘ │
│         │                  │            │
│         └────────┬─────────┘            │
│                  ▼                      │
│          Combined Score (1-100)         │
│          requires_human_review          │
└─────────────────────────────────────────┘
       │
       ▼
  If requires_human_review = true
       │
       ▼
  UiPath Maestro Case escalates
  to procurement security team
```

## UiPath Components Used

- **UiPath Maestro Case** — orchestrates the vendor review case lifecycle (intake → analysis → human review → decision → closure)
- **UiPath Agent Builder** — wraps VendorGuard AI API as a native UiPath agent
- **UiPath API Workflows** — calls `POST /analyze-vendor` and routes the result
- **Human-in-the-loop** — cases with `requires_human_review: true` pause and assign to a security analyst

**Coding Agents:** Built entirely with **Claude Code** (UiPath for Coding Agents) — from architecture to implementation to testing.

## API

### `POST /analyze-vendor`

```json
{
  "vendor_name": "Notion",
  "website": "https://notion.so"
}
```

**Response:**
```json
{
  "vendor_name": "Notion",
  "website": "https://notion.so",
  "security_score": 82,
  "key_findings": [
    "SOC2 certification detected",
    "ISO27001 certification detected",
    "Hosted on AWS (US/EU regions)",
    "Valid SSL certificate (expires 2025-12-01)",
    "No breach history found",
    "Active bug bounty program on HackerOne (12 open reports)"
  ],
  "requires_human_review": false,
  "details": {
    "saas_audit": { ... },
    "threat_intel": { ... }
  },
  "timestamp": "2026-06-22T10:30:00Z"
}
```

### `GET /health`
```json
{"status": "ok", "service": "VendorGuard AI"}
```

## Setup

### Prerequisites

- Python 3.11+
- Groq API key (free at [console.groq.com](https://console.groq.com))

### Installation

```bash
git clone https://github.com/YOUR_USERNAME/vendorguard-ai
cd vendorguard-ai

python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### Running

```bash
python run.py
# Server starts at http://localhost:8000
```

**Test the API:**
```bash
curl -X POST http://localhost:8000/analyze-vendor \
  -H "Content-Type: application/json" \
  -d '{"vendor_name": "Notion", "website": "https://notion.so"}'
```

**Interactive API docs:** http://localhost:8000/docs

## Project Structure

```
vendorguard/
├── agents/
│   ├── saas_auditor.py      # Agent A: scrapes vendor website for security signals
│   └── threat_intel.py      # Agent B: breach DB, bug bounty, domain risk, SSL
├── api/
│   └── main.py              # FastAPI app with /analyze-vendor endpoint
├── config/
│   └── settings.py          # Pydantic settings (reads from .env)
├── tests/                   # Test suite
├── uipath/                  # UiPath integration files
├── run.py                   # Server entry point
├── requirements.txt
├── .env.example
└── LICENSE                  # MIT
```

## How It Uses Claude Code (Bonus Points)

This entire project was built using **Claude Code** as a coding agent through the UiPath for Coding Agents integration:

- Agent architecture designed with Claude Code
- Both LangChain agents (`saas_auditor.py`, `threat_intel.py`) written by Claude Code
- FastAPI orchestration layer written by Claude Code  
- README, tests, and UiPath integration files generated by Claude Code

Claude Code acted as the primary developer, with the human developer acting as product manager and reviewer — demonstrating the exact human-AI collaboration model that UiPath Maestro Case is designed to support.

## License

MIT — see [LICENSE](LICENSE)
