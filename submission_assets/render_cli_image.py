"""
VendorGuard AI — CLI Dashboard → PNG Image
Captures terminal output of evaluate_vendor.py and renders it as a styled image.
"""
import os, sys, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent
ROOT = Path(__file__).parent.parent

os.environ["GROQ_API_KEY"] = "placeholder"  # force mock mode for instant render

# ── Capture CLI output (strip ANSI) ─────────────────────────────────────────
import re

def strip_ansi(text: str) -> str:
    return re.sub(r'\x1b\[[0-9;]*m', '', text)

result = subprocess.run(
    [sys.executable, "evaluate_vendor.py", "Microsoft", "https://microsoft.com"],
    cwd=ROOT,
    capture_output=True,
    text=True,
    env={**os.environ},
)
raw_text = strip_ansi(result.stdout + result.stderr)
lines = raw_text.splitlines()

# ── Render to image ──────────────────────────────────────────────────────────
BG        = (13, 17, 23)       # GitHub dark
FG        = (201, 209, 217)    # default text
CYAN      = (88, 166, 255)     # headers
GREEN     = (63, 185, 80)      # good findings
RED       = (248, 81, 73)      # warnings
YELLOW    = (210, 153, 34)     # moderate
DIM       = (110, 118, 125)    # dim text
MAGENTA   = (188, 140, 255)    # mode label

FONT_SIZE = 18
PADDING   = 28
LINE_H    = 24

# Try to find a monospace font
def get_font(size):
    candidates = [
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/cour.ttf",
        "C:/Windows/Fonts/lucon.ttf",
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()

font = get_font(FONT_SIZE)

# Filter to non-empty lines and truncate
visible = [l for l in lines if l.strip()][:52]

img_w = 900
img_h = PADDING * 2 + LINE_H * (len(visible) + 2)
img = Image.new("RGB", (img_w, img_h), BG)
draw = ImageDraw.Draw(img)

# Title bar
draw.rectangle([0, 0, img_w, 36], fill=(30, 35, 42))
for i, dot_x, col in [(0, 16, (255, 95, 87)), (1, 36, (255, 189, 46)), (2, 56, (39, 201, 63))]:
    draw.ellipse([dot_x-7, 11, dot_x+7, 25], fill=col)
draw.text((80, 9), "Terminal — VendorGuard AI", font=get_font(14), fill=FG)

y = 44
for line in visible:
    ll = line.lower()
    if line.startswith("-") and len(line) > 20:
        col = CYAN
    elif "vendorguard ai" in ll and "enterprise" in ll:
        col = CYAN
    elif ll.strip().startswith("*") and any(w in ll for w in ("soc2","iso","fedramp","hipaa","aes","tls","mfa","zero-trust","bug bounty","no breach","valid","certified")):
        col = GREEN
    elif ll.strip().startswith("*") and any(w in ll for w in ("warning","critical","breach detected","invalid","high risk")):
        col = RED
    elif "[!]" in line:
        col = RED
    elif "[ok]" in line:
        col = GREEN
    elif any(w in ll for w in ("#","trusted","moderate","high risk")) and "/100" in ll:
        col = GREEN if "trusted" in ll else (YELLOW if "moderate" in ll else RED)
    elif "mock" in ll or "mode" in ll.split(":")[0] if ":" in ll else False:
        col = MAGENTA
    elif "[i]" in line or "no groq" in ll:
        col = YELLOW
    elif line.strip().startswith("*"):
        col = FG
    elif "uipath" in ll or "maestro" in ll or "localhost" in ll:
        col = CYAN
    elif "built with" in ll:
        col = DIM
    else:
        col = FG

    draw.text((PADDING, y), line[:95], font=font, fill=col)
    y += LINE_H

out_path = OUT / "cli_dashboard.png"
img.save(out_path, "PNG")
print(f"Saved: {out_path}")
print(f"Image size: {img_w}x{img_h}")
