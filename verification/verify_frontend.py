from playwright.sync_api import sync_playwright
import time
import threading
import uvicorn
from scrollarr.app import app

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8003, log_level="critical")

def verify_frontend():
    # Start server in thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Wait for startup
    time.sleep(5)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 1. Check Tasks Page
        print("Navigating to Tasks page...")
        page.goto("http://127.0.0.1:8003/system/tasks")
        page.wait_for_selector("h1:has-text('Scheduled Tasks')")
        page.screenshot(path="verification/tasks_page.png")
        print("Tasks page screenshot captured.")

        # 2. Check Menu Structure
        print("Checking sidebar menu...")
        # Expand System menu if needed (though implementation defaults to expanded on /system/*)
        # Verify "System" header exists
        if page.is_visible("button#header-system"):
             print("System menu header visible.")
        else:
             print("System menu header NOT visible.")

        # 3. Check Activity Page
        print("Navigating to Activity page...")
        page.goto("http://127.0.0.1:8003/activity")
        page.wait_for_selector("h1:has-text('Activity')")

        # Click History tab
        page.click("button#history-tab")
        # Wait for table
        page.wait_for_selector("table")
        time.sleep(2) # Wait for fetch
        page.screenshot(path="verification/activity_page.png")
        print("Activity page screenshot captured.")

        browser.close()

if __name__ == "__main__":
    verify_frontend()
