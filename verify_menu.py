from playwright.sync_api import sync_playwright
import time
import sys

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        print("Navigating to dashboard...")
        try:
            page.goto("http://localhost:8000/", timeout=10000)

            # Check for security modal and dismiss it
            if page.is_visible("#security-modal"):
                print("Dismissing security modal...")
                page.click("text=No Login")
                # Wait for modal to disappear
                page.wait_for_selector("#security-modal", state="hidden")
                print("Security modal dismissed.")

            # Check for migration modal and dismiss it (skip)
            if page.is_visible("#migration-modal"):
                 print("Dismissing migration modal...")
                 page.click("text=Skip for Now")
                 page.wait_for_selector("#migration-modal", state="hidden")
                 print("Migration modal dismissed.")

            page.screenshot(path="debug_menu_initial.png")

            # Initial state: Stories open, others closed
            print("Checking initial state on Dashboard...")
            if not page.is_visible("#menu-stories"):
                print("FAIL: Stories menu should be visible on dashboard.")
            else:
                print("PASS: Stories menu is visible.")

            if page.is_visible("#menu-activity"):
                print("FAIL: Activity menu should be hidden.")
            else:
                print("PASS: Activity menu is hidden.")

            if page.is_visible("#menu-settings"):
                print("FAIL: Settings menu should be hidden.")
            else:
                print("PASS: Settings menu is hidden.")

            # Interaction: Click Activity
            print("Clicking Activity header...")
            page.click("#header-activity", timeout=5000)

            # Wait for transition if any
            time.sleep(0.5)

            if not page.is_visible("#menu-activity"):
                print("FAIL: Activity menu should be visible after click.")
            else:
                print("PASS: Activity menu is visible.")

            if page.is_visible("#menu-stories"):
                print("FAIL: Stories menu should be hidden after opening Activity.")
            else:
                print("PASS: Stories menu is hidden.")

            # Interaction: Click Activity again (toggle off)
            print("Clicking Activity header again...")
            page.click("#header-activity", timeout=5000)
            time.sleep(0.5)

            if page.is_visible("#menu-activity"):
                print("FAIL: Activity menu should be hidden after second click.")
            else:
                print("PASS: Activity menu is hidden.")

            # Navigation: Go to Settings
            print("Navigating to /settings...")
            page.goto("http://localhost:8000/settings", timeout=10000)

            if not page.is_visible("#menu-settings"):
                print("FAIL: Settings menu should be visible on settings page.")
            else:
                print("PASS: Settings menu is visible.")

            if page.is_visible("#menu-stories"):
                print("FAIL: Stories menu should be hidden on settings page.")
            else:
                print("PASS: Stories menu is hidden.")

            # Navigation: Go to Naming Settings (subheader)
            print("Navigating to /settings/naming...")
            page.goto("http://localhost:8000/settings/naming", timeout=10000)

            if not page.is_visible("#menu-settings"):
                print("FAIL: Settings menu should be visible on naming settings page.")
            else:
                print("PASS: Settings menu is visible.")

            page.screenshot(path="verification_menu.png")
            print("Screenshot saved to verification_menu.png")

        except Exception as e:
            print(f"Error: {e}")
            page.screenshot(path="debug_menu_error.png")
            print("Screenshot saved to debug_menu_error.png")
            sys.exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    run()
