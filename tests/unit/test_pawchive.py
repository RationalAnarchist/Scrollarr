import unittest
from unittest.mock import MagicMock, patch
from scrollarr.sources.pawchive import PawchiveSource
from datetime import datetime

class TestPawchiveSource(unittest.TestCase):
    def setUp(self):
        self.pawchive = PawchiveSource()

    def test_identify(self):
        self.assertTrue(self.pawchive.identify("https://pawchive.st/patreon/user/93759290"))
        self.assertFalse(self.pawchive.identify("https://kemono.cr/patreon/user/93759290"))

    @patch('playwright.sync_api.sync_playwright')
    def test_get_metadata(self, mock_sync_playwright):
        mock_playwright_context_manager = MagicMock()
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()

        mock_sync_playwright.return_value = mock_playwright_context_manager
        mock_playwright_context_manager.__enter__.return_value = mock_playwright
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        mock_page.evaluate.return_value = None

        html = """
        <html>
            <body>
                <h1 class="user-header__name"><span>Test Artist</span></h1>
                <div class="user-header__avatar"><img src="/icons/user/123.jpg"></div>
            </body>
        </html>
        """
        mock_page.content.return_value = html

        metadata = self.pawchive.get_metadata("https://pawchive.st/patreon/user/123")

        self.assertEqual(metadata['title'], "Test Artist")
        self.assertEqual(metadata['author'], "Test Artist")
        self.assertEqual(metadata['cover_url'], "https://pawchive.st/icons/user/123.jpg")
