import unittest
from unittest.mock import MagicMock, patch
from scrollarr.sources.inkitt import InkittSource

class TestInkittSource(unittest.TestCase):
    def setUp(self):
        self.source = InkittSource()

    def test_identify(self):
        self.assertTrue(self.source.identify("https://www.inkitt.com/stories/123"))
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
                <h1>Inkitt Story Title</h1>
                <a href="/users/123">Inkitt Author</a>
                <div class="story-summary">Inkitt summary here.</div>
                <div class="story-cover"><img src="//image.url/cover.jpg"></div>
                <a href="/genres/scifi">Sci-Fi</a>
                <a href="/tags/aliens">Aliens</a>
            </body>
        </html>
        """
        mock_page.content.return_value = html

        metadata = self.source.get_metadata("https://www.inkitt.com/stories/123")

        self.assertEqual(metadata['title'], "Inkitt Story Title")
        self.assertEqual(metadata['author'], "Inkitt Author")
        self.assertEqual(metadata['description'], "Inkitt summary here.")
        self.assertIn("Sci-Fi", metadata['tags'])
        self.assertIn("Aliens", metadata['tags'])
        self.assertEqual(metadata['cover_url'], "//image.url/cover.jpg")

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

        html = """
        <html>
            <body>
                <ul class="chapter-list">
                    <li class="chapter-list-item">
                        <a href="/stories/123/chapters/1">Chapter 1: The Beginning</a>
                    </li>
                    <li class="chapter-list-item">
                        <a href="/stories/123/chapters/2">Chapter 2: Next Step</a>
                    </li>
                </ul>
            </body>
        </html>
        """
        mock_page.content.return_value = html
        mock_page.evaluate.return_value = [] # Not used if list found in HTML

        chapters = self.source.get_chapter_list("https://www.inkitt.com/stories/123")

        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0]['title'], "Chapter 1: The Beginning")
        self.assertEqual(chapters[0]['url'], "https://www.inkitt.com/stories/123/chapters/1")
        self.assertEqual(chapters[1]['title'], "Chapter 2: Next Step")

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
                <div id="story-text">
                    <p>It was a dark and stormy night.</p>
                </div>
            </body>
        </html>
        """
        mock_page.content.return_value = html

        content = self.source.get_chapter_content("https://www.inkitt.com/stories/123/chapters/1")
        self.assertIn("dark and stormy night", content)

    @patch('playwright.sync_api.sync_playwright')
    def test_search(self, mock_sync_playwright):
        pass

if __name__ == '__main__':
    unittest.main()
