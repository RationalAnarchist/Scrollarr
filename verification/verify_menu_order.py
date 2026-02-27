from playwright.sync_api import sync_playwright
import time
import threading
import uvicorn
from scrollarr.app import app

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8005, log_level="critical")

def verify_frontend():
    # Start server in thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Wait for startup
    time.sleep(5)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("Navigating to dashboard...")
        page.goto("http://127.0.0.1:8005/")

        # Check Menu Order
        # We expect "Settings" to appear before "System"

        # Get all sidebar headers
        headers = page.locator("nav > div > button").all_inner_texts()
        print(f"Found headers: {headers}")

        clean_headers = [h.split('\n')[0].strip() for h in headers] # Clean up
        print(f"Clean headers: {clean_headers}")

        try:
            settings_idx = clean_headers.index("Settings")
            system_idx = clean_headers.index("System")

            if settings_idx < system_idx:
                print("PASS: Settings appears before System")
            else:
                print(f"FAIL: Settings (index {settings_idx}) appears AFTER System (index {system_idx})")
        except ValueError as e:
            print(f"FAIL: Could not find headers. {e}")

        # Try to dismiss security modal if it exists
        if page.is_visible("#security-modal"):
             print("Security modal detected. Skipping submenu interaction.")
             # We can infer correct template rendering from the header order for now,
             # as Playwright cannot easily interact with obscured elements in this headless setup without more complex logic.
             # The primary verification is the order, which we checked above.

             # But we can try to verify the HTML structure directly for the submenu order
             # Selector for System menu links
             system_menu_html = page.inner_html("#menu-system")

             # Simple string index check
             api_idx = system_menu_html.find("API Reference")
             tasks_idx = system_menu_html.find("Tasks")
             status_idx = system_menu_html.find("System Status")

             if api_idx < tasks_idx < status_idx:
                 print("PASS: System submenu order (HTML check) is correct: API -> Tasks -> Status")
             else:
                 print(f"FAIL: System submenu order incorrect. Indices: API={api_idx}, Tasks={tasks_idx}, Status={status_idx}")

        else:
            # Check System Submenu Order via interaction
            # Expand system menu
            page.click("button#header-system")
            time.sleep(0.5)

            # Get links in system menu
            system_links = page.locator("#menu-system > a").all_inner_texts()
            clean_links = [l.strip() for l in system_links]
            print(f"System links: {clean_links}")

            expected_order = ["API Reference", "Tasks", "System Status"]

            # Normalize for comparison
            normalized_links = []
            for link in clean_links:
                if "API Reference" in link: normalized_links.append("API Reference")
                elif "Tasks" in link: normalized_links.append("Tasks")
                elif "System Status" in link: normalized_links.append("System Status")

            if normalized_links == expected_order:
                print("PASS: System submenu order is correct")
            else:
                print(f"FAIL: System submenu order incorrect. Expected {expected_order}, got {normalized_links}")

        browser.close()

if __name__ == "__main__":
    verify_frontend()
