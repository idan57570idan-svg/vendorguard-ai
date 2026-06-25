"""
VendorGuard AI — Demo Video Generator
Creates a professional 90-second demo video using Pillow frames + imageio-ffmpeg.
No external ffmpeg required — imageio bundles its own.
"""
import os, math, textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import imageio.v3 as iio
import imageio

OUT   = Path(__file__).parent
VIDEO = OUT / "vendorguard_demo.mp4"

W, H  = 1280, 720
FPS   = 24

# ── Colour palette ────────────────────────────────────────────────────────────
BG_DARK    = (10, 14, 20)
BG_CARD    = (22, 27, 34)
BG_BAR     = (30, 35, 42)
ACCENT     = (88, 166, 255)
GREEN      = (63, 185, 80)
RED        = (248, 81, 73)
YELLOW     = (210, 153, 34)
MAGENTA    = (188, 140, 255)
FG         = (201, 209, 217)
DIM        = (100, 110, 120)
WHITE      = (230, 237, 243)
UIPATH_RED = (250, 70, 22)

# ── Fonts ─────────────────────────────────────────────────────────────────────
def font(size, bold=False):
    candidates = [
        ("C:/Windows/Fonts/segoeui.ttf",    "C:/Windows/Fonts/segoeuib.ttf"),
        ("C:/Windows/Fonts/calibri.ttf",    "C:/Windows/Fonts/calibrib.ttf"),
        ("C:/Windows/Fonts/consola.ttf",    "C:/Windows/Fonts/consolab.ttf"),
        ("C:/Windows/Fonts/arial.ttf",      "C:/Windows/Fonts/arialbd.ttf"),
    ]
    for reg, bld in candidates:
        try:
            path = bld if bold else reg
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()

F_TITLE    = font(56, bold=True)
F_HEAD     = font(34, bold=True)
F_BODY     = font(22)
F_BOLD     = font(22, bold=True)
F_SMALL    = font(16)
F_MONO     = font(18)
F_MONO_SM  = font(14)

# ── Drawing helpers ───────────────────────────────────────────────────────────
def new_frame():
    img = Image.new("RGB", (W, H), BG_DARK)
    d   = ImageDraw.Draw(img)
    # Subtle top gradient bar
    for i in range(4):
        d.rectangle([0, i, W, i+1], fill=(20+i*3, 25+i*3, 33+i*3))
    return img, d

def draw_title_bar(d, text):
    d.rectangle([0, 0, W, 48], fill=BG_BAR)
    for x, col in [(20, (255,95,87)), (44, (255,189,46)), (68, (39,201,63))]:
        d.ellipse([x-8, 16, x+8, 32], fill=col)
    d.text((90, 12), text, font=F_SMALL, fill=DIM)

def center_text(d, y, text, fnt, fill=FG):
    bbox = d.textbbox((0, 0), text, font=fnt)
    x = (W - (bbox[2] - bbox[0])) // 2
    d.text((x, y), text, font=fnt, fill=fill)

def badge(d, x, y, text, bg, fg=WHITE):
    bbox = d.textbbox((0, 0), text, font=F_SMALL)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    pad = 10
    d.rounded_rectangle([x, y, x+tw+pad*2, y+th+pad], radius=6, fill=bg)
    d.text((x+pad, y+pad//2), text, font=F_SMALL, fill=fg)
    return x + tw + pad*2 + 12

def score_bar_draw(d, x, y, score, width=380, height=22):
    filled = int(score / 100 * width)
    col = GREEN if score >= 75 else (YELLOW if score >= 50 else RED)
    d.rounded_rectangle([x, y, x+width, y+height], radius=6, fill=(40,46,56))
    if filled > 0:
        d.rounded_rectangle([x, y, x+filled, y+height], radius=6, fill=col)
    label = f"{score}/100"
    d.text((x+width+14, y), label, font=F_BOLD, fill=col)

def card(d, x, y, w, h, title=None):
    d.rounded_rectangle([x, y, x+w, y+h], radius=10, fill=BG_CARD)
    d.rounded_rectangle([x, y, x+w, y+h], radius=10, outline=(40,48,58), width=1)
    if title:
        d.text((x+16, y+12), title, font=F_SMALL, fill=DIM)

# ── Frame generators ──────────────────────────────────────────────────────────

def slide_title(t):
    img, d = new_frame()
    # Animated gradient diagonal line
    alpha = abs(math.sin(t * 1.5))
    ax = int(W * alpha)
    d.line([ax-200, 0, ax, H], fill=(30, 40, 55), width=3)

    # Logo / brand
    center_text(d, 130, "VendorGuard AI", F_TITLE, WHITE)
    center_text(d, 210, "Automated Vendor Security Reviews", F_HEAD, ACCENT)

    # Tags row
    bx = 200
    for tag, col in [("LangGraph", (50,60,100)), ("FastAPI", (20,70,80)),
                     ("UiPath Maestro", (80,30,20)), ("Claude Code", (50,40,90))]:
        bx = badge(d, bx, 290, tag, col)

    # Subtitle
    center_text(d, 360, "Two AI agents. One decision. Zero spreadsheets.", F_BODY, FG)
    center_text(d, 400, "AgentHack 2026  |  Track 1: UiPath Maestro Case", F_SMALL, DIM)

    # UiPath highlight
    d.rounded_rectangle([W//2-200, 460, W//2+200, 510], radius=8, fill=UIPATH_RED)
    center_text(d, 473, "Built with UiPath for Coding Agents", F_SMALL, WHITE)

    draw_title_bar(d, "VendorGuard AI — AgentHack 2026")
    return img

def slide_problem(progress):
    img, d = new_frame()
    draw_title_bar(d, "The Problem")
    d.text((80, 70), "The Vendor Security Review Bottleneck", font=F_HEAD, fill=RED)

    rows = [
        ("Time per vendor", "2–4 hours of manual work"),
        ("Vendors per quarter", "~50 vendors to vet"),
        ("Analyst cost", "$80 / hour"),
        ("Quarterly cost", "$8,000–$16,000 burned"),
        ("Annual cost", "$32,000–$64,000 wasted"),
    ]

    visible = int(len(rows) * min(1.0, progress * 2))
    card(d, 80, 120, W-160, 320)
    for i, (label, val) in enumerate(rows[:visible]):
        y = 142 + i*56
        col = RED if "cost" in label.lower() else FG
        d.text((110, y), label, font=F_BODY, fill=DIM)
        d.text((430, y), val, font=F_BOLD, fill=col)

    if progress > 0.6:
        d.text((80, 470), "And when a vendor slips through?", font=F_BOLD, fill=YELLOW)
        d.text((80, 510), "Average data breach cost: $4.45M  (IBM Security Report 2024)", font=F_BODY, fill=FG)

    return img

def slide_solution(progress):
    img, d = new_frame()
    draw_title_bar(d, "The Solution")
    center_text(d, 60, "VendorGuard AI", F_HEAD, ACCENT)
    center_text(d, 108, "Vendor analysis in <2 seconds, not 4 hours", F_BODY, FG)

    # Architecture flow
    boxes = [
        (70,  200, "Procurement\nRequest",    BG_CARD,    FG),
        (280, 200, "FastAPI\nOrchestrator",   (20,40,70), ACCENT),
        (490, 200, "Agent A\nSaaS Auditor",   (20,60,30), GREEN),
        (700, 200, "Agent B\nThreat Intel",   (60,20,20), RED),
        (490, 420, "Risk Score\n1 – 100",     (50,30,80), MAGENTA),
        (700, 420, "UiPath\nMaestro Case",    (80,25,10), UIPATH_RED),
    ]
    arrows = [(0,1),(1,2),(1,3),(2,4),(3,4),(4,5)]
    centers = {}

    visible_boxes = int(len(boxes) * min(1.0, progress * 1.8))
    visible_arrows = int(len(arrows) * max(0, (progress - 0.4) * 3))

    for i, (x, y, label, bg, fg) in enumerate(boxes[:visible_boxes]):
        bw, bh = 170, 80
        d.rounded_rectangle([x, y, x+bw, y+bh], radius=10, fill=bg)
        d.rounded_rectangle([x, y, x+bw, y+bh], radius=10, outline=fg, width=1)
        centers[i] = (x+bw//2, y+bh//2)
        for li, line in enumerate(label.split("\n")):
            lx = x + bw//2 - d.textbbox((0,0),line,font=F_SMALL)[2]//2
            d.text((lx, y+14+li*22), line, font=F_SMALL, fill=fg)

    for i, (a, b) in enumerate(arrows[:visible_arrows]):
        if a in centers and b in centers:
            d.line([centers[a], centers[b]], fill=DIM, width=2)

    if progress > 0.85:
        d.text((80, 560), "Auto-Approve (score >= 70)  ->  Robot syncs to ERP", font=F_SMALL, fill=GREEN)
        d.text((80, 590), "Human Review (score < 70)   ->  48h SLA Maestro Task", font=F_SMALL, fill=YELLOW)

    return img

def slide_cli_demo(progress):
    img, d = new_frame()
    draw_title_bar(d, "python evaluate_vendor.py Microsoft https://microsoft.com")

    lines = [
        ("", DIM),
        ("  [i] No GROQ_API_KEY detected -- running in MOCK mode (demo data)", YELLOW),
        ("", DIM),
        ("----------------------------------------------------------------", ACCENT),
        ("  VendorGuard AI  *  Enterprise Vendor Security Assessment", ACCENT),
        ("----------------------------------------------------------------", ACCENT),
        ("  Vendor  :  Microsoft", WHITE),
        ("  Website :  https://microsoft.com", ACCENT),
        ("  Mode    :  MOCK", MAGENTA),
        ("", DIM),
        ("--- Risk Score ---", ACCENT),
        ("  ####################################....  96/100  [TRUSTED]", GREEN),
        ("", DIM),
        ("--- UiPath Maestro Case Decision ---", ACCENT),
        ("  [OK] AUTO-APPROVED", GREEN),
        ("  * Vendor approved automatically -- no human review required", GREEN),
        ("  * UiPath robot will sync approval to ERP procurement module", GREEN),
        ("", DIM),
        ("--- Compliance Certifications ---", ACCENT),
        ("  * SOC2      * ISO27001   * PCI-DSS", GREEN),
        ("  * FedRAMP   * HIPAA      * GDPR     * CCPA", GREEN),
        ("", DIM),
        ("--- Breach History ---", ACCENT),
        ("  * No breach history found in monitored databases", GREEN),
    ]

    visible = int(len(lines) * min(1.0, progress * 1.6))
    y = 58
    for text, col in lines[:visible]:
        d.text((50, y), text, font=F_MONO_SM, fill=col)
        y += 22

    return img

def slide_api_demo(progress):
    img, d = new_frame()
    draw_title_bar(d, "POST http://localhost:8000/analyze-vendor")

    d.text((80, 70), "FastAPI — Swagger UI", font=F_HEAD, fill=ACCENT)

    # Request panel
    card(d, 60, 120, 540, 240, "REQUEST")
    req_lines = [
        'POST /analyze-vendor',
        'Content-Type: application/json',
        '',
        '{',
        '  "vendor_name": "Stripe",',
        '  "website": "https://stripe.com"',
        '}',
    ]
    for i, line in enumerate(req_lines):
        col = ACCENT if line.startswith("POST") else (GREEN if '"' in line else FG)
        d.text((80, 150+i*24), line, font=F_MONO_SM, fill=col)

    # Response panel
    if progress > 0.45:
        card(d, 620, 120, 600, 440, "RESPONSE  200 OK")
        resp = [
            '{',
            '  "vendor_name": "Stripe",',
            '  "security_score": 94,',
            '  "requires_human_review": false,',
            '  "mode": "mock",',
            '  "key_findings": [',
            '    "PCI DSS Level 1 confirmed",',
            '    "SOC2 Type II certified",',
            '    "No breach history on record",',
            '    "HackerOne: $50K max bounty"',
            '  ],',
            '  "timestamp": "2026-06-25T..."',
            '}',
        ]
        vis2 = int(len(resp) * min(1.0, (progress - 0.45) * 3))
        for i, line in enumerate(resp[:vis2]):
            col = GREEN if any(w in line for w in ('"94"','false','confirmed','certified','No breach')) else (ACCENT if '"' in line else FG)
            d.text((640, 148+i*24), line, font=F_MONO_SM, fill=col)

    if progress > 0.85:
        d.text((80, 390), "Response time: < 200ms", font=F_BOLD, fill=GREEN)
        d.text((80, 425), "Ready for UiPath API Workflow connector", font=F_SMALL, fill=DIM)

    return img

def slide_maestro(progress):
    img, d = new_frame()
    draw_title_bar(d, "UiPath Maestro Case — Vendor Review Lifecycle")
    center_text(d, 60, "5-Stage Automated Case Workflow", F_HEAD, UIPATH_RED)

    stages = [
        ("Intake",        "Request received",         (40,40,50), FG),
        ("AI Analysis",   "VendorGuard API called",   (20,40,70), ACCENT),
        ("Human Review",  "48h SLA analyst queue",    (60,45,10), YELLOW),
        ("Auto-Approved", "Robot syncs to ERP",       (20,60,30), GREEN),
        ("Rejected",      "Requestor notified",       (70,20,20), RED),
    ]

    vis = int(len(stages) * min(1.0, progress * 1.8))
    bw, bh, gap = 200, 90, 30
    total_w = len(stages) * bw + (len(stages)-1) * gap
    sx = (W - total_w) // 2

    for i, (name, desc, bg, fg) in enumerate(stages[:vis]):
        x = sx + i*(bw+gap)
        y = 170
        d.rounded_rectangle([x, y, x+bw, y+bh], radius=10, fill=bg)
        d.rounded_rectangle([x, y, x+bw, y+bh], radius=10, outline=fg, width=2)
        cx = x + bw//2 - d.textbbox((0,0),name,font=F_SMALL)[2]//2
        d.text((cx, y+14), name, font=F_SMALL, fill=fg)
        for li, ln in enumerate(textwrap.wrap(desc, 20)):
            cx2 = x + bw//2 - d.textbbox((0,0),ln,font=font(12))[2]//2
            d.text((cx2, y+42+li*16), ln, font=font(12), fill=DIM)
        if i > 0:
            ax = x - gap//2
            d.line([(ax-gap//2+2, y+bh//2), (ax+gap//2-2, y+bh//2)], fill=DIM, width=2)
            d.polygon([(ax+gap//2-2, y+bh//2-5), (ax+gap//2+4, y+bh//2), (ax+gap//2-2, y+bh//2+5)], fill=DIM)

    if progress > 0.7:
        card(d, 80, 300, W-160, 200)
        rows = [
            ("API Workflow",      "Calls POST /analyze-vendor, maps score + findings to case fields"),
            ("Human Task Form",   "Analyst sees full AI report: score, certs, breach history, findings"),
            ("SLA Enforcement",   "48-hour countdown tracked automatically — escalates if breached"),
            ("Notifications",     "Email to requestor on every stage transition (Maestro templates)"),
        ]
        for i, (lbl, desc) in enumerate(rows):
            y = 322 + i*42
            d.text((110, y), lbl+":", font=F_BOLD, fill=ACCENT)
            d.text((340, y), desc, font=F_SMALL, fill=FG)

    return img

def slide_scores(progress):
    img, d = new_frame()
    draw_title_bar(d, "Mock Mode — 8 Enterprise Vendor Profiles")
    center_text(d, 60, "Instant Results — Zero Setup Required", F_HEAD, ACCENT)

    vendors = [
        ("Microsoft",   96, GREEN),
        ("Google",      95, GREEN),
        ("Stripe",      94, GREEN),
        ("Salesforce",  91, GREEN),
        ("Slack",       89, GREEN),
        ("Notion",      82, GREEN),
        ("Zoom",        77, YELLOW),
        ("Adobe",       71, YELLOW),
    ]

    vis = int(len(vendors) * min(1.0, progress * 2))
    col_w = (W - 160) // 2
    for i, (name, score, col) in enumerate(vendors[:vis]):
        row, side = divmod(i, 4)
        x = 80 + side * (col_w + 20)
        y = 130 + row * 120
        card(d, x, y, col_w, 100)
        d.text((x+16, y+12), name, font=F_BOLD, fill=WHITE)
        score_bar_draw(d, x+16, y+46, score, width=col_w-100)
        label = "AUTO-APPROVE" if score >= 70 else "HUMAN REVIEW"
        lcol  = GREEN if score >= 70 else YELLOW
        d.text((x+16, y+76), label, font=font(13), fill=lcol)

    return img

def slide_coding_agents(progress):
    img, d = new_frame()
    draw_title_bar(d, "Built with Claude Code — UiPath for Coding Agents")
    center_text(d, 60, "Human-AI Co-Development", F_HEAD, MAGENTA)

    if progress > 0.1:
        # Terminal window
        card(d, 80, 110, W-160, 340)
        d.rounded_rectangle([80, 110, W-80, 150], radius=8, fill=(30,35,42))
        for xd, col in [(110,(255,95,87)),(134,(255,189,46)),(158,(39,201,63))]:
            d.ellipse([xd-8,125,xd+8,141], fill=col)
        d.text((175, 129), "Claude Code  |  UiPath for Coding Agents", font=F_SMALL, fill=DIM)

        conv = [
            ("> ", ACCENT,  "Build a LangGraph agent that scrapes SOC2 certs from vendor websites"),
            ("", GREEN,     "[Claude Code] Creating agents/saas_auditor.py with 5 tools..."),
            ("", GREEN,     "[Claude Code] Migrating from deprecated AgentExecutor to LangGraph 1.x..."),
            ("> ", ACCENT,  "Add offline mock mode for 8 major vendors so judges can demo without an API key"),
            ("", GREEN,     "[Claude Code] Writing _MOCK_PROFILES + _generate_mock_response() in api/main.py..."),
            ("> ", ACCENT,  "Fix UnicodeEncodeError on Windows cp1255 terminals"),
            ("", GREEN,     "[Claude Code] Replacing all Unicode symbols with ASCII equivalents..."),
            ("", MAGENTA,   "9/9 tests passing. All systems go."),
        ]
        vis2 = int(len(conv) * min(1.0, (progress - 0.1) * 1.8))
        for i, (prefix, col, text) in enumerate(conv[:vis2]):
            d.text((110, 162+i*35), prefix+text, font=F_MONO_SM, fill=col)

    if progress > 0.85:
        d.rounded_rectangle([80, 480, W-80, 540], radius=8, fill=(30,20,50))
        center_text(d, 494, "Every line of this codebase was written through natural language with Claude Code", F_SMALL, MAGENTA)
        center_text(d, 518, "That's exactly the model UiPath Maestro Case enables at enterprise scale", F_SMALL, DIM)

    return img

def slide_cta(t):
    img, d = new_frame()
    # Pulsing accent border
    pulse = 0.5 + 0.5 * math.sin(t * 3)
    border_col = tuple(int(c * pulse) for c in ACCENT)
    d.rectangle([0, 0, W, 6], fill=border_col)
    d.rectangle([0, H-6, W, H], fill=border_col)

    center_text(d, 100, "VendorGuard AI", F_TITLE, WHITE)
    center_text(d, 185, "Vendor security reviews in seconds, not days.", F_BODY, FG)

    bx = 200
    for tag, col in [("Open Source", (30,60,30)), ("MIT License", (30,30,60)),
                     ("Python 3.14", (20,50,70)), ("LangGraph 1.x", (50,30,80))]:
        bx = badge(d, bx, 250, tag, col)

    center_text(d, 320, "Track 1 — UiPath Maestro Case", F_HEAD, UIPATH_RED)
    center_text(d, 380, "AgentHack 2026  |  $50,000 Prize Pool", F_BODY, YELLOW)

    d.rounded_rectangle([W//2-280, 440, W//2+280, 500], radius=10, fill=(20,50,30))
    center_text(d, 454, "github.com/[your-username]/vendorguard-ai", F_BOLD, GREEN)

    center_text(d, 540, "Built with Claude Code (UiPath for Coding Agents)", F_SMALL, DIM)
    draw_title_bar(d, "VendorGuard AI — AgentHack 2026")
    return img

# ── Assemble video ─────────────────────────────────────────────────────────────

def ease(t): return t * t * (3 - 2 * t)  # smoothstep

slides = [
    # (generator_fn, duration_seconds)
    (slide_title,         4.0),
    (slide_problem,       6.0),
    (slide_solution,      7.0),
    (slide_cli_demo,      7.0),
    (slide_api_demo,      7.0),
    (slide_maestro,       8.0),
    (slide_scores,        6.0),
    (slide_coding_agents, 7.0),
    (slide_cta,           5.0),
]

total_frames = sum(int(dur * FPS) for _, dur in slides)
print(f"Rendering {total_frames} frames @ {FPS}fps ({sum(d for _,d in slides):.0f}s)...")

frames = []
for idx, (gen, dur) in enumerate(slides):
    n = int(dur * FPS)
    print(f"  Slide {idx+1}/{len(slides)}: {gen.__name__} ({n} frames)")
    for f in range(n):
        t = f / max(1, n - 1)
        progress = ease(t)
        if gen == slide_title or gen == slide_cta:
            frame_img = gen(t * dur)
        else:
            frame_img = gen(progress)
        frames.append(frame_img)

print(f"Writing video: {VIDEO}")
writer_kw = dict(fps=FPS, quality=8, macro_block_size=8)
with imageio.get_writer(str(VIDEO), format="ffmpeg", mode="I", **writer_kw) as writer:
    for i, frm in enumerate(frames):
        if i % (FPS * 5) == 0:
            print(f"  Encoding frame {i}/{total_frames}...")
        writer.append_data(__import__('numpy').array(frm))

size_mb = VIDEO.stat().st_size / 1_048_576
print(f"\nDone! {VIDEO.name}  ({size_mb:.1f} MB)")
