"""
VendorGuard AI — Final Demo Video Builder
==========================================
Pipeline:
  1. Generate AI voiceover with edge-tts (en-US-AndrewNeural)
  2. Build animated visuals (Pillow frames) timed to audio length
  3. Mux audio + video with bundled ffmpeg
  4. Output: submission_assets/VendorGuard_Final_Demo.mp4
"""
import asyncio, os, math, textwrap, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import imageio.v3 as iio
import imageio
import numpy as np

OUT   = Path(__file__).parent
ROOT  = Path(__file__).parent.parent
FFMPEG = None  # resolved below

# ─────────────────────────────────────────────────────────────────────────────
# 0. Resolve bundled ffmpeg
# ─────────────────────────────────────────────────────────────────────────────
try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
    print(f"[ffmpeg] {FFMPEG}")
except Exception as e:
    raise RuntimeError("imageio-ffmpeg not found. Run: pip install imageio[ffmpeg]") from e

# ─────────────────────────────────────────────────────────────────────────────
# 1. VOICEOVER SCRIPT  (tight, punchy — ~2 min 20 sec)
# ─────────────────────────────────────────────────────────────────────────────
SCRIPT = """
Welcome to VendorGuard AI.

Every quarter, your procurement team receives dozens of vendor onboarding requests.
Each one requires a manual security review — checking SOC2 certs, breach history,
SSL status, hosting regions. For 50 vendors per quarter, that's 200 hours of analyst time.
Over $16,000 burned every three months on spreadsheets.

VendorGuard AI solves this in seconds, not days.

Here's how it works. Two LangGraph AI agents run in parallel.

Agent A — the SaaS Auditor — scrapes the vendor's public website and trust pages.
It detects compliance certifications: SOC2, ISO27001, PCI-DSS, FedRAMP, HIPAA, and GDPR.
It maps hosting regions and evaluates over 30 security signals.

Agent B — the Threat Intel agent — checks breach history, bug bounty programs on HackerOne
and Bugcrowd, domain risk indicators, and live SSL certificate status.

A FastAPI orchestrator combines both scores into a security score from 1 to 100,
then hands off to UiPath Maestro Case.

Watch this. We run Microsoft through the CLI dashboard.

Score: 96 out of 100. Seven compliance certifications confirmed — SOC2, ISO27001,
FedRAMP, PCI-DSS, HIPAA, GDPR, and CCPA. Zero breach history. Auto-approved.
UiPath Robot syncs to ERP immediately.

Now let's try Adobe.

Score: 71. The 2013 breach of 153 million accounts is flagged.
VendorGuard routes this to the human review stage in Maestro Case.
A security analyst gets the full AI report — 48-hour SLA, tracked automatically.

This is how UiPath Maestro Case works with VendorGuard:
Five stages — Intake, AI Analysis, Human Review, Auto-Approved, Rejected.
The API Workflow connector calls our endpoint, maps the response to case fields,
and triggers the right path automatically. No human touches the keyboard for
trusted vendors. High-risk vendors get the scrutiny they deserve.

One more thing. This entire system was built with Claude Code, through UiPath
for Coding Agents. Every agent, every endpoint, every test — written through
natural language interaction. Human intent, AI execution.

VendorGuard AI. Vendor security reviews in seconds, not days.
Built on UiPath Maestro Case. Powered by LangGraph. Co-authored by Claude Code.
""".strip()

# ─────────────────────────────────────────────────────────────────────────────
# 2. GENERATE VOICEOVER
# ─────────────────────────────────────────────────────────────────────────────
VOICE_FILE = OUT / "voiceover.mp3"

async def _tts():
    import edge_tts
    communicate = edge_tts.Communicate(SCRIPT, voice="en-US-AndrewNeural",
                                        rate="+8%", pitch="-2Hz")
    await communicate.save(str(VOICE_FILE))

if not VOICE_FILE.exists():
    print("[1/4] Generating voiceover with edge-tts (en-US-AndrewNeural)...")
    asyncio.run(_tts())
    print(f"      Saved {VOICE_FILE.name} ({VOICE_FILE.stat().st_size//1024} KB)")
else:
    print(f"[1/4] Voiceover exists — skipping ({VOICE_FILE.stat().st_size//1024} KB)")

# Get audio duration via ffprobe
def audio_duration(path: Path) -> float:
    res = subprocess.run(
        [FFMPEG.replace("ffmpeg", "ffprobe") if "ffprobe" in FFMPEG else FFMPEG,
         "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True
    )
    # ffprobe may not be alongside ffmpeg; fall back to ffmpeg itself
    if not res.stdout.strip():
        res = subprocess.run(
            [FFMPEG, "-i", str(path), "-f", "null", "-"],
            capture_output=True, text=True
        )
        import re
        m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", res.stderr)
        if m:
            return int(m.group(1))*3600 + int(m.group(2))*60 + float(m.group(3))
        return 140.0  # fallback
    return float(res.stdout.strip())

DURATION = audio_duration(VOICE_FILE)
print(f"      Audio duration: {DURATION:.1f}s")

# ─────────────────────────────────────────────────────────────────────────────
# 3. BUILD ANIMATED VISUALS
# ─────────────────────────────────────────────────────────────────────────────
W, H, FPS = 1280, 720, 24

# Colours
BG        = (10, 14, 20)
BG_CARD   = (20, 26, 35)
BG_BAR    = (28, 33, 42)
ACCENT    = (88, 166, 255)
GREEN     = (56, 185, 80)
RED       = (248, 81, 73)
YELLOW    = (210, 160, 34)
MAGENTA   = (180, 130, 255)
FG        = (200, 208, 218)
DIM       = (90, 100, 112)
WHITE     = (230, 238, 245)
UIPATH    = (250, 70, 22)

def _font(size, bold=False):
    candidates = [
        ("C:/Windows/Fonts/segoeui.ttf",  "C:/Windows/Fonts/segoeuib.ttf"),
        ("C:/Windows/Fonts/calibri.ttf",  "C:/Windows/Fonts/calibrib.ttf"),
        ("C:/Windows/Fonts/arial.ttf",    "C:/Windows/Fonts/arialbd.ttf"),
        ("C:/Windows/Fonts/consola.ttf",  "C:/Windows/Fonts/consolab.ttf"),
    ]
    for r, b in candidates:
        try:
            return ImageFont.truetype(b if bold else r, size)
        except Exception:
            pass
    return ImageFont.load_default()

FA  = _font(52, True)
FB  = _font(32, True)
FC  = _font(22)
FD  = _font(22, True)
FE  = _font(16)
FM  = _font(15)  # mono

def nf():
    img = Image.new("RGB", (W, H), BG)
    return img, ImageDraw.Draw(img)

def cx(d, y, txt, f, col):
    bb = d.textbbox((0,0), txt, font=f)
    d.text(((W-(bb[2]-bb[0]))//2, y), txt, font=f, fill=col)

def tbar(d, txt="VendorGuard AI — AgentHack 2026"):
    d.rectangle([0,0,W,44], fill=BG_BAR)
    for ox, c in [(18,(255,95,87)),(40,(255,189,46)),(62,(39,201,63))]:
        d.ellipse([ox-8,14,ox+8,30], fill=c)
    d.text((80, 13), txt, font=FE, fill=DIM)

def sbar(d, x, y, score, w=360, h=20):
    col = GREEN if score>=75 else (YELLOW if score>=50 else RED)
    d.rounded_rectangle([x,y,x+w,y+h], radius=6, fill=(38,44,54))
    if score:
        d.rounded_rectangle([x,y,x+int(score/100*w),y+h], radius=6, fill=col)
    d.text((x+w+12, y), f"{score}/100", font=FD, fill=col)

def ease(t): return t*t*(3-2*t)
def eio(t):  return t*t*t if t<0.5 else 1-(-2*t+2)**3/2  # ease-in-out cubic

# ── Asset loader (screenshots) ────────────────────────────────────────────────
_asset_cache = {}
def load_asset(name: str, size=(600,360)):
    if name in _asset_cache:
        return _asset_cache[name]
    p = OUT / name
    if p.exists():
        img = Image.open(p).convert("RGB").resize(size, Image.LANCZOS)
        _asset_cache[name] = img
        return img
    return None

# ── Slide definitions ──────────────────────────────────────────────────────────
# Each slide: (start_sec, end_sec, render_fn)

def s_intro(p):
    img, d = nf()
    tbar(d)
    # animated diagonal accent
    ax = int(W * ease(p))
    for i in range(3):
        d.line([(ax-160+i*8,0),(ax+i*8,H)], fill=(20+i*5,28+i*4,40+i*3), width=2)
    cx(d, 120, "VendorGuard AI", FA, WHITE)
    cx(d, 192, "Automated Vendor Security Reviews", FB, ACCENT)
    tags = [("LangGraph 1.x",(40,55,95)),("FastAPI",(15,65,75)),
            ("UiPath Maestro",(80,28,18)),("Claude Code",(55,38,95))]
    bx = 175
    for tag, bg in tags:
        bb = d.textbbox((0,0),tag,font=FE)
        tw = bb[2]-bb[0]+20
        if p > 0.3:
            d.rounded_rectangle([bx,280,bx+tw,306], radius=5, fill=bg)
            d.text((bx+10,283), tag, font=FE, fill=WHITE)
        bx += tw+10
    if p > 0.5:
        cx(d, 360, "Two AI agents. One decision. Zero spreadsheets.", FC, FG)
    if p > 0.7:
        d.rounded_rectangle([W//2-230,440,W//2+230,496], radius=9, fill=UIPATH)
        cx(d, 452, "Track 1 — UiPath Maestro Case  |  AgentHack 2026", FE, WHITE)
    return img

def s_problem(p):
    img, d = nf()
    tbar(d, "The Problem")
    d.text((70,60), "The Vendor Security Bottleneck", font=FB, fill=RED)
    rows = [
        ("Manual hours per vendor",   "2–4 hours"),
        ("Vendors per quarter",        "~50 vendors"),
        ("Analyst rate",               "$80 / hour"),
        ("Quarterly waste",            "$8,000–$16,000"),
    ]
    d.rounded_rectangle([60,118,W-60,400], radius=10, fill=BG_CARD)
    d.rounded_rectangle([60,118,W-60,400], radius=10, outline=(38,46,58), width=1)
    vis = int(len(rows) * min(1, p*2))
    for i,(lbl,val) in enumerate(rows[:vis]):
        y = 142+i*58
        col = RED if "waste" in lbl.lower() else FG
        d.text((90,y), lbl, font=FC, fill=DIM)
        d.text((480,y), val, font=FD, fill=col)
        d.line([(90,y+32),(W-80,y+32)], fill=(34,40,50), width=1)
    if p > 0.65:
        d.rounded_rectangle([60,420,W-60,490], radius=8, fill=(50,20,15))
        cx(d, 436, "Average data breach cost: $4.45M — IBM Security Report 2024", FE, YELLOW)
        cx(d, 458, "When a vendor slips through, the cost dwarfs the savings.", FE, FG)
    return img

def s_architecture(p):
    img, d = nf()
    tbar(d, "Architecture")
    cx(d, 54, "Dual-Agent LangGraph Pipeline", FB, ACCENT)
    nodes = [
        (90,  180, 170, 80, "Procurement\nRequest",  BG_CARD,        FG),
        (310, 180, 170, 80, "FastAPI\nOrchestrator", (18,38,68),     ACCENT),
        (530, 140, 170, 80, "Agent A\nSaaS Auditor", (15,55,25),     GREEN),
        (530, 260, 170, 80, "Agent B\nThreat Intel", (55,18,18),     RED),
        (750, 200, 170, 80, "Risk Score\n1 – 100",   (45,25,75),     MAGENTA),
        (970, 200, 170, 80, "Maestro\nCase",          (80,22,10),     UIPATH),
    ]
    arrows = [(0,1,"API"),(1,2,""),(1,3,""),(2,4,""),(3,4,""),(4,5,"route")]
    ctrs = {}
    vis_n = int(len(nodes)*min(1,p*1.6))
    vis_a = int(len(arrows)*max(0,(p-0.4)*2.5))
    for i,(x,y,bw,bh,lbl,bg,fg) in enumerate(nodes[:vis_n]):
        d.rounded_rectangle([x,y,x+bw,y+bh], radius=8, fill=bg)
        d.rounded_rectangle([x,y,x+bw,y+bh], radius=8, outline=fg, width=1)
        ctrs[i] = (x+bw//2, y+bh//2)
        for li,ln in enumerate(lbl.split("\n")):
            bb = d.textbbox((0,0),ln,font=FE)
            lx = x+(bw-(bb[2]-bb[0]))//2
            d.text((lx, y+16+li*20), ln, font=FE, fill=fg)
    for i,(a,b,lbl) in enumerate(arrows[:vis_a]):
        if a in ctrs and b in ctrs:
            ax1,ay1 = ctrs[a]; ax2,ay2 = ctrs[b]
            d.line([(ax1,ay1),(ax2,ay2)], fill=(60,70,85), width=2)
    if p > 0.85:
        d.rounded_rectangle([60,540,W-60,595], radius=8, fill=(15,40,20))
        d.text((80,554), "score >= 70  ->  AUTO-APPROVE (Robot syncs to ERP)", font=FE, fill=GREEN)
        d.text((80,574), "score  < 70  ->  HUMAN REVIEW (48h SLA Maestro task)", font=FE, fill=YELLOW)
    return img

def s_cli_microsoft(p):
    img, d = nf()
    tbar(d, "python evaluate_vendor.py Microsoft https://microsoft.com")
    lines = [
        ("", DIM),
        ("  [i] Running in MOCK mode (demo data)", YELLOW),
        ("", DIM),
        ("  ----------------------------------------------------------------", ACCENT),
        ("  VendorGuard AI  *  Enterprise Vendor Security Assessment", ACCENT),
        ("  ----------------------------------------------------------------", ACCENT),
        ("  Vendor  :  Microsoft", WHITE),
        ("  Website :  https://microsoft.com", ACCENT),
        ("  Mode    :  MOCK", MAGENTA),
        ("", DIM),
        ("  ---- Risk Score ----", ACCENT),
        ("  ####################################....  96/100  [TRUSTED]", GREEN),
        ("", DIM),
        ("  ---- UiPath Maestro Case Decision ----", ACCENT),
        ("  [OK] AUTO-APPROVED", GREEN),
        ("  * Vendor approved -- no human review required", GREEN),
        ("  * UiPath Robot syncs approval to ERP procurement module", GREEN),
        ("", DIM),
        ("  ---- Compliance Certifications ----", ACCENT),
        ("  * SOC2  * ISO27001  * PCI-DSS  * FedRAMP  * HIPAA  * GDPR  * CCPA", GREEN),
        ("", DIM),
        ("  ---- Breach History ----", ACCENT),
        ("  * No breach history found in monitored databases", GREEN),
    ]
    vis = int(len(lines)*min(1,p*1.5))
    y = 54
    for txt, col in lines[:vis]:
        d.text((40,y), txt, font=FM, fill=col)
        y += 22
    return img

def s_cli_adobe(p):
    img, d = nf()
    tbar(d, "python evaluate_vendor.py Adobe https://adobe.com")
    lines = [
        ("  [i] Running in MOCK mode", YELLOW),
        ("", DIM),
        ("  ----------------------------------------------------------------", ACCENT),
        ("  VendorGuard AI  *  Enterprise Vendor Security Assessment", ACCENT),
        ("  ----------------------------------------------------------------", ACCENT),
        ("  Vendor  :  Adobe", WHITE),
        ("  Website :  https://adobe.com", ACCENT),
        ("", DIM),
        ("  ---- Risk Score ----", ACCENT),
        ("  #############################...........  71/100  [MODERATE]", YELLOW),
        ("", DIM),
        ("  ---- UiPath Maestro Case Decision ----", ACCENT),
        ("  [!] ESCALATE TO HUMAN REVIEW", RED),
        ("  * Case routed to security_team queue", YELLOW),
        ("  * SLA: 48 hours for analyst review and sign-off", YELLOW),
        ("", DIM),
        ("  ---- Threat Findings ----", ACCENT),
        ("  * 2013 CRITICAL: 153M accounts breached -- payment data exposed", RED),
        ("  * Significant remediation: full re-architecture of auth systems", YELLOW),
        ("  * HackerOne: active since 2018, 800+ reports resolved", FG),
        ("  * SSL/TLS: VALID -- DigiCert EV, 195 days remaining", GREEN),
    ]
    vis = int(len(lines)*min(1,p*1.5))
    y = 54
    for txt, col in lines[:vis]:
        d.text((40,y), txt, font=FM, fill=col)
        y += 24
    return img

def s_api(p):
    img, d = nf()
    tbar(d, "POST http://localhost:8000/analyze-vendor")
    cx(d, 54, "FastAPI — Live API Demo", FB, ACCENT)

    # Load screenshot if available
    shot = load_asset("api_response.png", size=(W-120, H-140))
    if shot and p > 0.15:
        alpha = min(1.0, (p-0.15)*4)
        overlay = Image.new("RGB", (W,H), BG)
        overlay.paste(shot, (60, 115))
        img = Image.blend(img, overlay, alpha)
        d = ImageDraw.Draw(img)
        tbar(d, "POST http://localhost:8000/analyze-vendor")
        cx(d, 54, "FastAPI — Live API Demo", FB, ACCENT)
    else:
        # Draw schematic if no screenshot
        d.rounded_rectangle([60,110,580,380], radius=8, fill=BG_CARD)
        d.text((80,124), "REQUEST", font=FE, fill=DIM)
        req = ['POST /analyze-vendor','Content-Type: application/json','',
               '{','  "vendor_name": "Stripe",','  "website": "https://stripe.com"','}']
        for i,l in enumerate(req):
            col = ACCENT if l.startswith("POST") else (GREEN if '"' in l else FG)
            d.text((80,148+i*26), l, font=FM, fill=col)
        if p > 0.4:
            d.rounded_rectangle([620,110,W-40,500], radius=8, fill=BG_CARD)
            d.text((640,124), "RESPONSE  200 OK", font=FE, fill=GREEN)
            resp = ['{',' "security_score": 94,',
                    ' "requires_human_review": false,',
                    ' "mode": "mock",',
                    ' "key_findings": [',
                    '   "PCI DSS Level 1 confirmed",',
                    '   "SOC2 Type II certified",',
                    '   "No breach history",',
                    ' ]','}']
            vis2 = int(len(resp)*min(1,(p-0.4)*3))
            for i,l in enumerate(resp[:vis2]):
                col = GREEN if any(w in l for w in ('94','false','confirmed','No breach')) else FG
                d.text((640,148+i*26), l, font=FM, fill=col)
    return img

def s_maestro(p):
    img, d = nf()
    tbar(d, "UiPath Maestro Case — 5-Stage Workflow")
    cx(d, 54, "Automated Case Orchestration", FB, UIPATH)
    stages = [
        ("Intake",       FG,      BG_CARD),
        ("AI Analysis",  ACCENT,  (16,36,64)),
        ("Hum. Review",  YELLOW,  (56,44,10)),
        ("Auto-Approve", GREEN,   (16,54,24)),
        ("Rejected",     RED,     (64,18,18)),
    ]
    bw, bh, gap = 195, 88, 14
    total_w = len(stages)*bw + (len(stages)-1)*gap
    sx = (W-total_w)//2
    vis = int(len(stages)*min(1,p*1.8))
    for i,(name,col,bg) in enumerate(stages[:vis]):
        x = sx+i*(bw+gap); y = 165
        d.rounded_rectangle([x,y,x+bw,y+bh], radius=9, fill=bg)
        d.rounded_rectangle([x,y,x+bw,y+bh], radius=9, outline=col, width=2)
        bb = d.textbbox((0,0),name,font=FD)
        d.text((x+(bw-(bb[2]-bb[0]))//2, y+30), name, font=FD, fill=col)
        if i>0 and i-1 in range(vis):
            ax = sx+(i-1)*(bw+gap)+bw
            d.polygon([(ax+2,y+bh//2-5),(ax+gap-2,y+bh//2),(ax+2,y+bh//2+5)], fill=DIM)
    if p > 0.5:
        d.rounded_rectangle([60,290,W-60,560], radius=9, fill=BG_CARD)
        items = [
            ("API Workflow",    ACCENT,  "Calls POST /analyze-vendor — maps score, findings, review flag"),
            ("Human Task Form", YELLOW,  "Analyst sees full AI report: certs, breach history, score"),
            ("48h SLA",         RED,     "Countdown auto-tracked — escalates if analyst doesn't act"),
            ("Notifications",   GREEN,   "Email to requestor on every stage transition (Maestro)"),
            ("Robot Action",    MAGENTA, "Auto-approve path: Robot syncs decision to ERP via API"),
        ]
        vis2 = int(len(items)*min(1,(p-0.5)*3))
        for i,(lbl,col,desc) in enumerate(items[:vis2]):
            y = 312+i*46
            d.text((90,y), lbl+":", font=FD, fill=col)
            d.text((310,y), desc, font=FE, fill=FG)
    return img

def s_scores(p):
    img, d = nf()
    tbar(d, "Mock Mode — 8 Enterprise Vendor Profiles")
    cx(d, 54, "Zero Setup — Full Demo Without API Key", FB, ACCENT)
    vendors = [
        ("Microsoft", 96, GREEN),("Google",     95, GREEN),
        ("Stripe",    94, GREEN),("Salesforce",  91, GREEN),
        ("Slack",     89, GREEN),("Notion",      82, GREEN),
        ("Zoom",      77, YELLOW),("Adobe",      71, YELLOW),
    ]
    cw = (W-160)//2
    vis = int(len(vendors)*min(1,p*2))
    for i,(name,score,col) in enumerate(vendors[:vis]):
        row,side = divmod(i,4)
        x = 80+side*(cw+20); y = 128+row*128
        d.rounded_rectangle([x,y,x+cw,y+110], radius=8, fill=BG_CARD)
        d.rounded_rectangle([x,y,x+cw,y+110], radius=8, outline=(38,46,58), width=1)
        d.text((x+16,y+12), name, font=FD, fill=WHITE)
        sbar(d, x+16, y+50, score, w=cw-110, h=18)
        lbl = "AUTO-APPROVE" if score>=70 else "HUMAN REVIEW"
        d.text((x+16,y+82), lbl, font=_font(13), fill=col)
    return img

def s_coding_agents(p):
    img, d = nf()
    tbar(d, "Claude Code — UiPath for Coding Agents")
    cx(d, 54, "Built With Human-AI Co-Development", FB, MAGENTA)
    if p > 0.1:
        d.rounded_rectangle([60,110,W-60,490], radius=9, fill=BG_CARD)
        d.rounded_rectangle([60,110,W-60,150], radius=9, fill=BG_BAR)
        d.text((88,124), "Claude Code  |  VendorGuard AI Session", font=FE, fill=DIM)
        conv = [
            ("> ", ACCENT,   "Build two LangGraph agents for vendor security analysis"),
            ("",  GREEN,     "[CC] Writing agents/saas_auditor.py with 5 scraping tools..."),
            ("",  GREEN,     "[CC] Writing agents/threat_intel.py with 4 threat tools..."),
            ("> ", ACCENT,   "Migrate from deprecated AgentExecutor to LangGraph 1.x"),
            ("",  GREEN,     "[CC] Replacing AgentExecutor with create_react_agent..."),
            ("> ", ACCENT,   "Add offline mock mode for 8 vendors — judges need zero setup"),
            ("",  GREEN,     "[CC] Writing _MOCK_PROFILES + _generate_mock_response()..."),
            ("> ", ACCENT,   "Fix UnicodeEncodeError on Windows cp1255 terminals"),
            ("",  GREEN,     "[CC] Replacing all Unicode symbols with ASCII equivalents..."),
            ("",  MAGENTA,   "9/9 tests passing. Ship it."),
        ]
        vis2 = int(len(conv)*min(1,(p-0.1)*1.5))
        for i,(pre,col,txt) in enumerate(conv[:vis2]):
            d.text((88, 162+i*32), pre+txt, font=FM, fill=col)
    if p > 0.88:
        d.rounded_rectangle([60,508,W-60,566], radius=8, fill=(28,15,50))
        cx(d, 520, "Every line: natural language -> Claude Code -> production code", FE, MAGENTA)
        cx(d, 544, "That's the future of enterprise automation with UiPath Maestro Case", FE, DIM)
    return img

def s_outro(p):
    img, d = nf()
    pulse = 0.5+0.5*math.sin(p*math.pi*4)
    bc = tuple(int(c*pulse) for c in ACCENT)
    d.rectangle([0,0,W,5], fill=bc); d.rectangle([0,H-5,W,H], fill=bc)
    tbar(d)
    cx(d, 100, "VendorGuard AI", FA, WHITE)
    cx(d, 175, "Vendor security reviews in seconds, not days.", FC, FG)
    outro_tags = [
        ("Open Source",  (28,55,28)),
        ("MIT License",  (24,44,24)),
        ("Python 3.14",  (18,48,68)),
        ("LangGraph 1.x",(44,28,80)),
    ]
    bx = 185
    for tag, bg in outro_tags:
        bb = d.textbbox((0,0), tag, font=FE)
        tw = bb[2]-bb[0]+20
        d.rounded_rectangle([bx,255,bx+tw,281], radius=5, fill=bg)
        d.text((bx+10,258), tag, font=FE, fill=WHITE)
        bx += tw+10
    cx(d, 320, "Track 1 — UiPath Maestro Case", FB, UIPATH)
    cx(d, 376, "AgentHack 2026  |  $50,000 Prize Pool", FC, YELLOW)
    d.rounded_rectangle([W//2-280,440,W//2+280,498], radius=9, fill=(14,44,24))
    cx(d, 452, "github.com/[your-username]/vendorguard-ai", FD, GREEN)
    cx(d, 548, "Built with Claude Code (UiPath for Coding Agents)", FE, DIM)
    return img

# Timing map — tuned to ~140s voiceover
TIMELINE = [
    # (start_sec, end_sec, render_fn)
    (0,    10,   s_intro),
    (10,   26,   s_problem),
    (26,   44,   s_architecture),
    (44,   68,   s_cli_microsoft),
    (68,   88,   s_cli_adobe),
    (88,   104,  s_api),
    (104,  124,  s_maestro),
    (124,  134,  s_scores),
    (134,  144,  s_coding_agents),
    (144,  DURATION, s_outro),
]

# ─────────────────────────────────────────────────────────────────────────────
# 4. RENDER FRAMES
# ─────────────────────────────────────────────────────────────────────────────
total_frames = int(DURATION * FPS)
print(f"\n[2/4] Rendering {total_frames} frames @ {FPS}fps ({DURATION:.1f}s)...")

RAW_VIDEO = OUT / "raw_visuals.mp4"

with imageio.get_writer(str(RAW_VIDEO), format="ffmpeg", mode="I",
                        fps=FPS, quality=9, macro_block_size=8) as writer:
    prev_img = None
    for fn in range(total_frames):
        t = fn / FPS
        # Find active slide + compute progress
        slide_fn = s_intro  # fallback
        progress = 0.0
        for s_start, s_end, sfn in TIMELINE:
            if s_start <= t < s_end:
                slide_fn = sfn
                progress = eio((t - s_start) / max(0.001, s_end - s_start))
                break
            if t >= s_end:
                slide_fn = sfn
                progress = 1.0

        frame_img = slide_fn(progress)

        # Cross-fade at slide boundaries (1s fade)
        if prev_img is not None:
            for s_start, s_end, _ in TIMELINE:
                fade_dur = min(0.8, (s_end - s_start) * 0.12)
                if abs(t - s_start) < fade_dur:
                    alpha = (t - s_start + fade_dur) / (fade_dur * 2)
                    alpha = max(0.0, min(1.0, alpha))
                    frame_img = Image.blend(prev_img, frame_img, alpha)
                    break

        if fn % (FPS * 10) == 0:
            pct = fn * 100 // total_frames
            print(f"      Frame {fn}/{total_frames}  ({pct}%)")
        writer.append_data(np.array(frame_img))
        prev_img = frame_img

print(f"      Saved {RAW_VIDEO.name} ({RAW_VIDEO.stat().st_size//1024} KB)")

# ─────────────────────────────────────────────────────────────────────────────
# 5. MUX AUDIO + VIDEO
# ─────────────────────────────────────────────────────────────────────────────
FINAL = OUT / "VendorGuard_Final_Demo.mp4"
print(f"\n[3/4] Muxing audio + video...")

cmd = [
    FFMPEG, "-y",
    "-i", str(RAW_VIDEO),
    "-i", str(VOICE_FILE),
    "-c:v", "copy",
    "-c:a", "aac", "-b:a", "192k",
    "-shortest",
    "-movflags", "+faststart",
    str(FINAL),
]
result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode != 0:
    print("FFMPEG stderr:", result.stderr[-2000:])
    raise RuntimeError("ffmpeg mux failed")

size_mb = FINAL.stat().st_size / 1_048_576
print(f"\n[4/4] Done!")
print(f"      {FINAL.name}")
print(f"      Duration: {DURATION:.1f}s  |  Size: {size_mb:.1f} MB")
print(f"\n      -> Upload this to YouTube/Vimeo for your Devpost submission.")
