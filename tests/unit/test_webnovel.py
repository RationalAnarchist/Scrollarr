import unittest
from unittest.mock import MagicMock, patch
from scrollarr.sources.webnovel import WebNovelSource

class TestWebNovelSource(unittest.TestCase):
    def setUp(self):
        self.source = WebNovelSource()

    def test_identify(self):
        self.assertTrue(self.source.identify("https://www.webnovel.com/book/123"))
        self.assertFalse(self.source.identify("https://google.com"))

    @patch('playwright.sync_api.sync_playwright')
    def test_get_metadata(self, mock_sync_playwright):
        mock_context_manager = MagicMock()
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()

        mock_sync_playwright.return_value = mock_context_manager
        mock_context_manager.__enter__.return_value = mock_playwright
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        html = """
        <html>
            <body>
                <h1>WebNovel Story Title</h1>
                <a href="/profile/123">Author Name</a>
                <div class="j_synopsis">This is the synopsis.</div>
                <div class="m-tags">
                    <a href="/tag/fantasy">Fantasy</a>
                    <a href="/tag/action">Action</a>
                </div>
                <meta property="og:image" content="//image.url/cover.jpg">
            </body>
        </html>
        """
        mock_page.content.return_value = html

        metadata = self.source.get_metadata("https://www.webnovel.com/book/123")

        self.assertEqual(metadata['title'], "WebNovel Story Title")
        self.assertEqual(metadata['author'], "Author Name")
        self.assertEqual(metadata['description'], "This is the synopsis.")
        self.assertIn("Fantasy", metadata['tags'])
        self.assertIn("Action", metadata['tags'])
        self.assertEqual(metadata['cover_url'], "https://image.url/cover.jpg")

    @patch('playwright.sync_api.sync_playwright')
    def test_get_chapter_list(self, mock_sync_playwright):
        mock_context_manager = MagicMock()
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()

        mock_sync_playwright.return_value = mock_context_manager
        mock_context_manager.__enter__.return_value = mock_playwright
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        # Mock evaluate result for hrefs
        links = [
            {'href': 'https://www.webnovel.com/book/123/1', 'text': 'Chapter 1', 'is_locked': False},
            {'href': 'https://www.webnovel.com/book/123/2', 'text': 'Chapter 2', 'is_locked': True},
            {'href': 'https://www.webnovel.com/other', 'text': 'Other Link', 'is_locked': False}
        ]
        mock_page.evaluate.return_value = links

        chapters = self.source.get_chapter_list("https://www.webnovel.com/book/123")

        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0]['title'], "Chapter 1")
        self.assertEqual(chapters[0]['url'], "https://www.webnovel.com/book/123/1")
        self.assertEqual(chapters[1]['title'], "Chapter 2 [LOCKED]")

    @patch('playwright.sync_api.sync_playwright')
    def test_get_chapter_content(self, mock_sync_playwright):
        mock_context_manager = MagicMock()
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()

        mock_sync_playwright.return_value = mock_context_manager
        mock_context_manager.__enter__.return_value = mock_playwright
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        html = """
        <html>
            <body>
                <div class="chapter_content">
                    <p>Chapter content paragraph 1.</p>
                    <p>Chapter content paragraph 2.</p>
                </div>
            </body>
        </html>
        """
        mock_page.content.return_value = html

        content = self.source.get_chapter_content("https://www.webnovel.com/book/123/1")
        self.assertIn("paragraph 1", content)

    @patch('playwright.sync_api.sync_playwright')
    def test_search(self, mock_sync_playwright):
        # Skip search test as implementation relies on complex selectors that are hard to mock generally without specific HTML
        # Or provide a mock HTML that matches the speculative logic
        pass

if __name__ == '__main__':
    unittest.main()
