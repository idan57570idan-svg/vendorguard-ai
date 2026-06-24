# VendorGuard AI — Demo Video Script
# UiPath AgentHack 2026 | Track 1: UiPath Maestro Case
# Runtime: ~5 minutes

---

## PRE-ROLL (0:00 – 0:10)
*Overlay: "VendorGuard AI | Built with Claude Code + UiPath for Coding Agents"*

---

## SCENE 1 — THE PROBLEM (0:10 – 1:00)

**[Screen: a spreadsheet with 40+ vendor rows, each partially filled]**

**VOICEOVER:**
> "Every quarter, your procurement team receives dozens of vendor onboarding requests.
> Each one requires a manual security review — checking SOC2 certs, breach history,
> hosting regions, SSL status. For 50 vendors per quarter, that's 100–200 hours of
> analyst time. At $80/hour, you're burning over $16,000 every quarter on spreadsheets."

**[Screen: calendar showing days of work, then a risk incident headline]**

> "And when a vendor slips through a gap — a silent breach, an expired cert,
> a missing GDPR DPA — the consequences dwarf the cost of proper review."

**[CUT TO: VendorGuard logo animation]**

> "VendorGuard AI solves this in seconds, not hours."

---

## SCENE 2 — ARCHITECTURE OVERVIEW (1:00 – 1:45)

**[Screen: ASCII architecture diagram from README, animated]**

**VOICEOVER:**
> "VendorGuard AI runs two independent LangGraph AI agents in parallel."

**[Highlight Agent A]**
> "Agent A — the SaaS Auditor — scrapes the vendor's public website, trust pages,
> and security documentation. It detects compliance certifications: SOC2, ISO27001,
> PCI-DSS, FedRAMP, HIPAA, GDPR. It maps hosting regions and scores 30+ security signals."

**[Highlight Agent B]**
> "Agent B — the Threat Intel agent — checks breach history, bug bounty programs
> on HackerOne and Bugcrowd, domain risk indicators, and live SSL/TLS certificate status."

**[Highlight FastAPI orchestrator]**
> "A FastAPI orchestrator combines both scores into a single security score from 1 to 100,
> then hands off to UiPath Maestro Case — auto-approving trusted vendors,
> or routing high-risk ones to a human security analyst queue with a 48-hour SLA."

---

## SCENE 3 — LIVE CLI DEMO (1:45 – 3:00)

**[Screen: terminal window, open folder C:\Users\USER\Desktop\vendorguard]**

**VOICEOVER:**
> "Let's see it run. First, a well-known enterprise vendor."

**[TYPE: python evaluate_vendor.py Adobe https://adobe.com]**
**[PAUSE — dashboard renders in terminal]**

> "Adobe scores 71 out of 100. The 2013 breach of 153 million accounts is flagged,
> along with their significant remediation effort. VendorGuard routes this to
> the human_review stage in Maestro Case — security analyst gets the full findings
> with a 48-hour SLA."

**[TYPE: python evaluate_vendor.py Microsoft https://microsoft.com]**
**[PAUSE — dashboard renders]**

> "Microsoft scores 96. Seven compliance certifications confirmed — SOC2, ISO27001,
> FedRAMP, PCI-DSS, HIPAA, GDPR, CCPA. Active bug bounty via MSRC.
> Zero-trust architecture enforced. Auto-approved — no human review needed.
> UiPath robot syncs this to your ERP procurement module automatically."

**[TYPE: python evaluate_vendor.py "Acme Corp" https://acmecorp.io]**
**[PAUSE — dashboard renders]**

> "An unknown vendor. Limited security documentation, unverified certs,
> medium domain risk. Routed to human review for a deeper questionnaire."

---

## SCENE 4 — API + SWAGGER DEMO (3:00 – 3:40)

**[Screen: browser open to http://localhost:8000/docs]**

**VOICEOVER:**
> "The same intelligence is exposed as a REST API — ready for UiPath Maestro Case
> to call directly via its API Workflow connector."

**[Expand POST /analyze-vendor, fill in Notion, click Execute]**

> "Notion — score 82. SOC2 and GDPR confirmed, ISO27001 in progress.
> Returned in under 200 milliseconds. The 'mode' field tells Maestro whether
> this is a live LLM result or a mock response — fully auditable."

**[Show the JSON response in the Swagger UI]**

> "Every field maps directly to a Maestro Case field — vendor name, score,
> key findings array, requires_human_review boolean, timestamp."

---

## SCENE 5 — UIPATH MAESTRO CASE (3:40 – 4:20)

**[Screen: UiPath Automation Cloud — Maestro Case UI]**

**VOICEOVER:**
> "Inside UiPath Maestro Case, the workflow is defined as a five-stage process."

**[Highlight Intake stage]**
> "Intake receives the vendor request — name, website, requestor, department."

**[Highlight AI Analysis stage]**
> "AI Analysis fires an API Workflow call to VendorGuard. The response populates
> the case automatically — score, findings, review flag."

**[Show the fork: auto_approved vs human_review]**
> "If score is 70 or above and no review flag — the vendor auto-approves.
> A UiPath Robot notifies the requestor and syncs to the ERP."
> "Below 70, or if a critical finding is detected — the case escalates
> to the security team queue. The analyst sees the full AI report right inside
> the Maestro task form. They approve, reject, or request more information.
> 48-hour SLA tracked automatically by Maestro."

---

## SCENE 6 — CODING AGENTS BONUS (4:20 – 4:50)

**[Screen: Claude Code terminal session]**

**VOICEOVER:**
> "One more thing. This entire architecture was built using Claude Code —
> UiPath's integration with Coding Agents."

**[Show Claude Code terminal with a natural-language command being typed]**
> "Every agent, every endpoint, every test — written through natural language
> conversation with Claude Code. The LangGraph migration, the mock mode,
> the CLI dashboard, the Maestro workflow JSON — all of it."

**[Show git log with commits]**
> "Human-AI co-development at its best. That's exactly the model
> UiPath Maestro Case enables for enterprise automation at scale."

---

## SCENE 7 — CLOSE (4:50 – 5:00)

**[Screen: final slide with GitHub URL, score badge, UiPath logo]**

**VOICEOVER:**
> "VendorGuard AI. Vendor security reviews in seconds, not days.
> Built on UiPath Maestro Case, powered by LangGraph, co-authored by Claude Code."

*Overlay: GitHub URL | AgentHack 2026 | Track 1: UiPath Maestro Case*

---

## RECORDING CHECKLIST

- [ ] Terminal font size: 16pt minimum for readability
- [ ] Window: 120 columns wide (fits the 64-char dashboard cleanly)
- [ ] Set GROQ_API_KEY=placeholder before recording (mock mode shows instant results)
- [ ] Pre-type commands, paste on camera to avoid typos
- [ ] Record at 1920x1080, export H.264 MP4
- [ ] Background music: subtle, under -20dB
- [ ] Total runtime: aim for 4:45–5:00

## COMMANDS TO RUN DURING RECORDING

```powershell
cd C:\Users\USER\Desktop\vendorguard

# Scene 3 — CLI demos (run in this order)
python evaluate_vendor.py Adobe https://adobe.com
python evaluate_vendor.py Microsoft https://microsoft.com
python evaluate_vendor.py "Acme Corp" https://acmecorp.io

# Scene 4 — Start server, then open browser to localhost:8000/docs
python run.py
```
