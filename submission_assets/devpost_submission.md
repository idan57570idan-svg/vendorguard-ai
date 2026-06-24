# VendorGuard AI — Devpost Submission

> Copy-paste each section directly into the corresponding Devpost field.

---

## Project Title
```
VendorGuard AI
```

## Track
```
Track 1 — UiPath Maestro Case
```

## Tagline
```
Vendor security reviews in seconds, not days — powered by LangGraph AI agents and UiPath Maestro Case.
```

---

## Inspiration

Every company that handles SOC2, ISO27001, HIPAA, or PCI-DSS compliance is legally required
to vet every third-party vendor before onboarding them. In practice, this means a security
analyst manually visiting websites, Googling breach histories, checking SSL certificates, and
filling spreadsheets — 2 to 4 hours per vendor, 50 vendors per quarter, $16,000+ burned every
three months on repetitive, error-prone work.

We built VendorGuard AI because we saw procurement teams delay critical vendor onboardings by
weeks waiting for security sign-off, and we knew that an AI agent — with the right tools and
the right orchestration layer — could compress that timeline from days to seconds while
actually being *more* thorough than a human analyst.

The deeper inspiration was UiPath Maestro Case itself: the idea that you can define a
business process as a structured case, inject AI decision-making at the right moment,
and still preserve the human-in-the-loop for cases where the stakes are too high for
full automation. That is exactly the architecture vendor security reviews need.

---

## What It Does

VendorGuard AI automates the full vendor security review lifecycle:

**1. Two parallel LangGraph AI agents analyze the vendor:**

- **Agent A — SaaS Auditor** scrapes the vendor's public website, trust pages, and security
  documentation. It detects compliance certifications (SOC2, ISO27001, PCI-DSS, FedRAMP,
  HIPAA, GDPR, CCPA), maps hosting regions (AWS / Azure / GCP), and evaluates 30+ security
  posture signals to produce a score contribution of 0–50.

- **Agent B — Threat Intel** checks breach history against a monitored database, evaluates
  bug bounty program exposure on HackerOne and Bugcrowd, scores domain risk based on TLD
  age and reputation, and performs a live SSL/TLS certificate inspection. It produces a
  threat score contribution of 0–50 and a `requires_human_review` flag.

**2. A FastAPI orchestrator** combines both agent scores into a final security score (1–100)
and assembles a `key_findings` list with all evidence.

**3. UiPath Maestro Case orchestrates the decision:**
- Score ≥ 70 and no review flag → **Auto-Approved**: UiPath Robot syncs the approval to the
  ERP procurement module and notifies the requestor automatically.
- Score < 70 or review flag raised → **Human Review**: The case is assigned to the
  `security_team` queue with a 48-hour SLA. The analyst sees the full AI-generated report
  inside the Maestro task form and approves, rejects, or requests more information.

**4. A CLI dashboard** (`evaluate_vendor.py`) lets anyone run a full assessment from the
terminal without starting the server — with ANSI color output, a visual risk score bar,
and a `--json` flag for piping into other systems.

---

## How We Built It

**Backend (Python 3.14):**
- `FastAPI 0.138` with Pydantic v2 for the REST API
- `LangGraph 1.x` (`langgraph.prebuilt.create_react_agent`) for both AI agents — we migrated
  away from the deprecated LangChain `AgentExecutor` pattern
- `Groq API` with `llama-3.3-70b-versatile` as the free-tier LLM backend (6,000 tokens/min)
- `BeautifulSoup4 + requests` for web scraping in Agent A
- A deterministic **offline mock mode**: when no GROQ_API_KEY is present, the system returns
  realistic enterprise vendor profiles for 8 major vendors (Microsoft 96, Google 95,
  Stripe 94, Salesforce 91, Slack 89, Notion 82, Zoom 77, Adobe 71) — ensuring judges
  always see a compelling, working demo with zero setup

**UiPath Integration:**
- `uipath/maestro_case_workflow.json` defines the full 5-stage case lifecycle, API call
  schema with response field mapping, human task form definition, SLA configuration,
  and notification templates for all stage transitions

**Coding Agents:**
- The entire project was built using **Claude Code** through **UiPath for Coding Agents**
- Every agent, endpoint, migration, test, and CLI script was produced through natural
  language interaction — human intent → Claude Code → working code

---

## Challenges We Ran Into

**LangChain 1.x breaking changes.** Midway through development, we discovered that
`AgentExecutor` and the old `create_react_agent` were fully removed in LangChain 1.x.
We had to migrate both agents to `langgraph.prebuilt.create_react_agent` with the new
`{"messages": [("human", prompt)]}` invocation format and `response["messages"][-1].content`
extraction pattern — a non-trivial refactor that Claude Code helped us navigate cleanly.

**Python 3.14 compatibility.** Pydantic-core requires Rust compilation, and `rustup` failed
on our environment. We resolved this by using flexible version pins (`>=2.11.0`) that
leveraged pre-built wheels already available for Python 3.14.5.

**Windows cp1255 terminal encoding.** The initial CLI dashboard used Unicode symbols
(•, █, →, ⚠, ✓) that caused `UnicodeEncodeError` on Windows terminals with cp1255 encoding.
We rewrote the entire symbol set to pure ASCII equivalents (`*`, `#`, `->`, `[!]`, `[OK]`)
while preserving the visual clarity of the dashboard.

**False-positive human review escalations.** Our initial `requires_human_review` logic
checked if the word "breach" appeared anywhere in findings — which meant "No breach history
found" triggered an escalation. We fixed this by checking the `threat_result` flag directly
and only triggering on strings like `"breach detected"` or findings starting with `"CRITICAL"`.

---

## Accomplishments That We're Proud Of

- **9/9 automated tests passing** on Python 3.14.5 with pytest — zero flaky tests
- **Offline mock mode** that produces realistic, differentiated vendor profiles
  deterministically — no API key, no server, just `python evaluate_vendor.py`
- **Full LangGraph 1.x migration** — we're on the current, non-deprecated architecture
- **UiPath Maestro Case workflow** ready to import — complete JSON with field mappings,
  human task forms, SLA definitions, and notification templates
- **Claude Code as a co-author** — we didn't just use AI to generate boilerplate.
  Every architectural decision, every bug fix, every migration was a conversation.
  The result is a codebase that reflects both human intent and AI execution quality.

---

## What We Learned

Building with LangGraph 1.x taught us the value of the new graph-based agent architecture
over the old sequential executor model. The ability to define tools, pass a system prompt,
and let the graph handle the ReAct loop internally makes agent code dramatically cleaner
and more maintainable.

More broadly, we learned that the hardest part of AI-powered automation is not the AI —
it's the integration layer. Getting the API response to map cleanly to Maestro Case fields,
getting the `requires_human_review` boolean to be exactly right (not too aggressive,
not too lenient), getting the CLI to work on every Windows terminal encoding — that is
where the real engineering work lives, and where Claude Code as a collaborative partner
genuinely accelerated our delivery.

---

## What's Next for VendorGuard AI

**Q3 2026 — Real-time threat feeds:**
- BreachDirectory / HaveIBeenPwned API for live breach lookups
- CISA KEV (Known Exploited Vulnerabilities) feed integration
- PDF export of full audit report for compliance archiving

**Q4 2026 — Enterprise features:**
- Vendor re-check scheduler (quarterly auto-refresh triggered by Maestro)
- Slack / Teams notifications for analyst escalations
- Multi-vendor batch processing (CSV upload → parallel Maestro cases)
- Vendor risk trend tracking over time (score history dashboard)

**2027 — Platform:**
- Native UiPath Marketplace listing
- ML model trained on historical breach pattern data for predictive scoring
- Multi-tenant SaaS offering with per-organization vendor databases

---

## Built With

`python` `fastapi` `langgraph` `langchain` `groq` `beautifulsoup4` `pydantic`
`uipath-maestro` `uipath-api-workflows` `uipath-for-coding-agents` `claude-code`
`pytest` `uvicorn` `requests`

---

## Links

- **GitHub:** [add your public repo URL here]
- **Demo Video:** [add YouTube/Vimeo URL here]
- **Presentation Deck:** [add Google Drive / OneDrive URL here]
