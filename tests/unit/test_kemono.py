import unittest
from unittest.mock import MagicMock, patch
from scrollarr.sources.kemono import KemonoSource
from datetime import datetime

class TestKemonoSource(unittest.TestCase):
    def setUp(self):
        self.kemono = KemonoSource()

    def test_identify(self):
        self.assertTrue(self.kemono.identify("https://kemono.su/fanbox/user/123"))
        self.assertTrue(self.kemono.identify("https://kemono.party/patreon/user/456"))
        self.assertFalse(self.kemono.identify("https://google.com"))

    @patch('playwright.sync_api.sync_playwright')
    def test_get_metadata(self, mock_sync_playwright):
        # Mock context manager
        mock_playwright_context_manager = MagicMock()
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()

        mock_sync_playwright.return_value = mock_playwright_context_manager
        mock_playwright_context_manager.__enter__.return_value = mock_playwright
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        # Force API failure to fallback to scraping
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

        metadata = self.kemono.get_metadata("https://kemono.su/fanbox/user/123")

        self.assertEqual(metadata['title'], "Test Artist")
        self.assertEqual(metadata['author'], "Test Artist")
        self.assertEqual(metadata['cover_url'], "https://kemono.cr/icons/user/123.jpg")

    @patch('playwright.sync_api.sync_playwright')
    def test_get_chapter_list(self, mock_sync_playwright):
        mock_playwright_context_manager = MagicMock()
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_sync_playwright.return_value = mock_playwright_context_manager
        mock_playwright_context_manager.__enter__.return_value = mock_playwright
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        # Mock API Responses via page.evaluate
        def mock_evaluate(script, *args):
            # print(f"DEBUG: script received: {script}")
            # 1. Tags - return empty list for simplicity
            if "/tags" in script:
                return {'success': True, 'data': []}

            # 2. Posts page 0
            if "/posts?o=0" in script:
                 return {'success': True, 'data': [
                    {'id': '100', 'title': 'Post 1', 'published': '2023-01-01T12:00:00', 'service': 'fanbox', 'user': '123'},
                    {'id': '101', 'title': 'Post 2', 'published': '2023-01-02T12:00:00', 'service': 'fanbox', 'user': '123'}
                ]}

            # 3. Posts page 50 (empty to stop loop)
            if "/posts?o=50" in script:
                return {'success': True, 'data': []}

            return {'success': False, 'error': 'Unknown script'}

        mock_page.evaluate.side_effect = mock_evaluate

        chapters = self.kemono.get_chapter_list("https://kemono.su/fanbox/user/123")

        # print(f"DEBUG: Chapters found: {len(chapters)}")

        self.assertEqual(len(chapters), 2)
        # Note: Sorted by date ascending
        self.assertEqual(chapters[0]['title'], "Post 1")
        # Code forces .cr domain
        self.assertEqual(chapters[0]['url'], "https://kemono.cr/fanbox/user/123/post/100")

        self.assertIsInstance(chapters[0]['published_date'], datetime)
        self.assertEqual(chapters[0]['published_date'].year, 2023)

    @patch('playwright.sync_api.sync_playwright')
    def test_get_chapter_content(self, mock_sync_playwright):
        mock_playwright_context_manager = MagicMock()
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()

        mock_sync_playwright.return_value = mock_playwright_context_manager
        mock_playwright_context_manager.__enter__.return_value = mock_playwright
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        # Mock page content for BeautifulSoup
        mock_page.content.return_value = "<html><body><div class='post__content'><p>Content</p></div></body></html>"

        # Mock query_selector
        mock_element = MagicMock()
        mock_element.inner_html.return_value = "<p>Content</p>"

        def query_selector_side_effect(selector):
            if selector == '.post__content':
                return mock_element
            if selector == '.post-content':
                return None
            if selector == '.post__thumbnail img':
                return None
            return None

        mock_page.query_selector.side_effect = query_selector_side_effect
        mock_page.query_selector_all.return_value = []

        content = self.kemono.get_chapter_content("https://kemono.su/post/1")
        self.assertIn("<p>Content</p>", content)

if __name__ == '__main__':
    unittest.main()
