"""
VendorGuard AI — Automated Screenshot Capture
Starts the FastAPI server, takes Playwright screenshots of Swagger UI and API responses.
"""
import os, sys, time, subprocess, json, textwrap
from pathlib import Path

OUT = Path(__file__).parent
os.environ["GROQ_API_KEY"] = "GROQ_API_KEY_PLACEHOLDER"

# ── Start server ────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
print("[1/4] Starting FastAPI server on port 8004...")
srv = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "api.main:app", "--port", "8004", "--host", "127.0.0.1"],
    cwd=ROOT,
    env={**os.environ},
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
time.sleep(4)

# ── Playwright screenshots ───────────────────────────────────────────────────
from playwright.sync_api import sync_playwright

print("[2/4] Taking Swagger UI screenshot...")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})

    # ── Swagger UI ──────────────────────────────────────────────────────────
    page.goto("http://127.0.0.1:8004/docs", wait_until="networkidle", timeout=15000)
    time.sleep(2)
    page.screenshot(path=str(OUT / "api_docs.png"), full_page=True)
    print("    Saved api_docs.png")

    # ── Expand POST /analyze-vendor ─────────────────────────────────────────
    print("[3/4] Expanding POST /analyze-vendor and running live demo...")
    try:
        page.click("text=POST /analyze-vendor", timeout=5000)
        time.sleep(0.8)
        page.click("text=Try it out", timeout=5000)
        time.sleep(0.5)
        textarea = page.query_selector("textarea.body-param__text")
        if textarea:
            textarea.fill('{"vendor_name": "Microsoft", "website": "https://microsoft.com"}')
        page.click("text=Execute", timeout=5000)
        time.sleep(3)
        page.screenshot(path=str(OUT / "api_response.png"), full_page=True)
        print("    Saved api_response.png")
    except Exception as e:
        print(f"    Warning: {e} — skipping api_response.png")

    # ── Health endpoint ─────────────────────────────────────────────────────
    page.goto("http://127.0.0.1:8004/health", wait_until="networkidle")
    time.sleep(0.5)
    page.screenshot(path=str(OUT / "api_health.png"))
    print("    Saved api_health.png")

    browser.close()

srv.terminate()
print("[4/4] Server stopped. Screenshots complete.")
