import threading
import subprocess
import logging

logger = logging.getLogger(__name__)

class BrowserManager:
    """
    A thread-local singleton for Playwright to ensure that long-running jobs (like batch downloads)
    can reuse a single Chromium instance instead of launching and closing it for every single chapter.
    """
    _local = threading.local()

    @classmethod
    def get_browser(cls):
        if not hasattr(cls._local, 'playwright') or cls._local.playwright is None:
            from playwright.sync_api import sync_playwright
            cls._local.playwright = sync_playwright().start()
            cls._local.browser = None

        if not hasattr(cls._local, 'browser') or cls._local.browser is None:
            try:
                cls._local.browser = cls._local.playwright.chromium.launch(headless=True)
            except Exception as e:
                if "Executable doesn't exist" in str(e):
                    logger.info("Playwright browsers not found. Installing...")
                    subprocess.run(["playwright", "install", "chromium"], check=True)
                    cls._local.browser = cls._local.playwright.chromium.launch(headless=True)
                else:
                    raise e
        
        return cls._local.browser

    @classmethod
    def get_page(cls, extra_headers=None):
        browser = cls.get_browser()
        if extra_headers:
            return browser.new_page(extra_http_headers=extra_headers)
        return browser.new_page()

    @classmethod
    def close(cls):
        try:
            if hasattr(cls._local, 'browser') and cls._local.browser:
                cls._local.browser.close()
                cls._local.browser = None
            if hasattr(cls._local, 'playwright') and cls._local.playwright:
                cls._local.playwright.stop()
                cls._local.playwright = None
        except Exception as e:
            logger.error(f"Error closing BrowserManager: {e}")
