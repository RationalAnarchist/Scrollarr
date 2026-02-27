from playwright.sync_api import sync_playwright, expect
import os

def verify_ui():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            print("Navigating to home...")
            page.goto("http://localhost:8000/")
            expect(page).to_have_title("Library - Scrollarr")

            print("Navigating to story details (ID 1)...")
            # We assume ID 1 exists from seed
            page.goto("http://localhost:8000/story/1")

            # 1. Check "Verify Content" button
            print("Checking Verify Content button...")
            verify_btn = page.get_by_role("button", name="Verify Content")
            expect(verify_btn).to_be_visible()

            # 2. Check "View" button for Chapter 1 (Downloaded)
            # Row for chapter 1
            # We can find row by text "Chapter 1"
            print("Checking View button...")
            c1_row = page.locator("tr", has_text="Chapter 1")
            view_btn = c1_row.locator("button[title='View Content']")
            expect(view_btn).to_be_visible()

            # Click view
            view_btn.click()

            # Check modal
            print("Checking Modal...")
            modal = page.locator("#content-modal")
            expect(modal).to_be_visible()
            expect(page.locator("#modal-title")).to_have_text("Chapter 1")

            # Wait for content load (mocked file response)
            # content should contain "This is the content of Chapter 1"
            expect(page.locator("#modal-content")).to_contain_text("This is the content of Chapter 1")

            # Close modal
            page.locator("#content-modal button").click()
            expect(modal).not_to_be_visible()

            # 3. Check "Re-download" button
            print("Checking Re-download button...")
            redownload_btn = c1_row.locator("button[title='Re-download']")
            expect(redownload_btn).to_be_visible()

            # Take screenshot
            page.screenshot(path="verification/story_ui.png", full_page=True)
            print("Screenshot saved to verification/story_ui.png")

        except Exception as e:
            print(f"Verification failed: {e}")
            page.screenshot(path="verification/error.png")
        finally:
            browser.close()

if __name__ == "__main__":
    verify_ui()
