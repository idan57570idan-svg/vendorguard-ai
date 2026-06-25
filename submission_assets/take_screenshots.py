"""Take Playwright screenshots of the running VendorGuard API."""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)

    # 1 — Swagger UI full page
    pg = b.new_page(viewport={"width": 1400, "height": 860})
    pg.goto("http://127.0.0.1:8005/docs", wait_until="networkidle", timeout=15000)
    time.sleep(2)
    pg.screenshot(path=str(OUT / "api_docs.png"), full_page=True)
    print("Saved api_docs.png")

    # 2 — POST /analyze-vendor expanded + executed
    try:
        pg.locator(".opblock-post").first.click(timeout=5000)
        time.sleep(1)
        pg.locator("button", has_text="Try it out").first.click(timeout=4000)
        time.sleep(0.5)
        ta = pg.locator("textarea.body-param__text").first
        ta.click()
        ta.fill('{"vendor_name": "Microsoft", "website": "https://microsoft.com"}')
        pg.locator("button", has_text="Execute").first.click(timeout=4000)
        time.sleep(5)
        pg.screenshot(path=str(OUT / "api_response.png"), full_page=True)
        print("Saved api_response.png")
    except Exception as exc:
        print(f"api_response skip: {exc}")

    # 3 — Health endpoint JSON
    pg.goto("http://127.0.0.1:8005/health")
    time.sleep(0.5)
    pg.screenshot(path=str(OUT / "api_health.png"))
    print("Saved api_health.png")

    # 4 — Root info endpoint
    pg.goto("http://127.0.0.1:8005/")
    time.sleep(0.5)
    pg.screenshot(path=str(OUT / "api_root.png"))
    print("Saved api_root.png")

    b.close()

print("All screenshots done.")
