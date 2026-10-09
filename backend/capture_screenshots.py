import os
import time
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "screenshots"))
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2  # High-DPI retina sharpness
        )
        page = context.new_page()

        print("1. Capturing Public Submit Portal...")
        page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        time.sleep(1)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "01_submit_report_portal.png"))

        print("2. Capturing Live PII Privacy Detection Alert...")
        page.select_option("#input-category", "Corruption")
        pii_text = "Contact Dr. Ramesh Sharma at ramesh.sharma@corp.com or +91 9876543210 regarding illicit vendor payments to employee RA20261009."
        page.fill("#input-description", pii_text)
        # Wait for debounce and PII pre-check response
        time.sleep(2)
        page.wait_for_selector("#pii-alert-banner:not(.hidden)", timeout=5000)
        time.sleep(1)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "02_pii_privacy_detection.png"))

        print("3. Submitting report and capturing Success Modal...")
        page.click("#btn-submit-report")
        page.wait_for_selector("#modal-success:not(.hidden)", timeout=10000)
        time.sleep(1)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "03_submission_success_modal.png"))

        print("4. Capturing Public Case Tracking Portal...")
        page.click("button:has-text('Track This Case Now')")
        page.wait_for_selector("#track-result-wrap:not(.hidden)", timeout=10000)
        time.sleep(1)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "04_case_tracking_portal.png"))

        print("5. Capturing Moderator Login Modal...")
        page.click("#nav-case-queue")
        page.wait_for_selector("#modal-login:not(.hidden)", timeout=5000)
        time.sleep(1)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "05_moderator_login_modal.png"))

        print("6. Logging in and capturing Moderator Dashboard...")
        page.fill("#input-mod-username", "moderator")
        page.fill("#input-mod-password", "WhistleDrop@2026")
        page.click("#btn-login-submit")
        page.wait_for_selector("#view-mod-overview.active", timeout=10000)
        time.sleep(2)  # Wait for table and stats fetch
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "06_moderator_dashboard.png"))

        print("7. Opening Case Dossier Inspector and capturing...")
        # Click on the first row in the queue table
        page.click("#queue-table-body tr")
        page.wait_for_selector("#modal-inspector:not(.hidden)", timeout=5000)
        time.sleep(1.5)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "07_case_dossier_inspector.png"))

        print("8. Scrolling Case Dossier to action controls...")
        page.eval_on_selector(".dossier-scroll-content", "el => el.scrollTop = el.scrollHeight")
        time.sleep(1)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "08_case_closure_and_action.png"))

        browser.close()
        print(f"All 8 screenshots successfully captured and saved to {SCREENSHOTS_DIR}!")

if __name__ == "__main__":
    run()
