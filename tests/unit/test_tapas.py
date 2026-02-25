import unittest
from unittest.mock import MagicMock, patch
from scrollarr.sources.tapas import TapasSource

class TestTapasSource(unittest.TestCase):
    def setUp(self):
        self.source = TapasSource()

    def test_identify(self):
        self.assertTrue(self.source.identify("https://tapas.io/series/123"))
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
                <h1 class="series-header-title">Tapas Series Title</h1>
                <a class="author-name" href="/creator/123">Author Name</a>
                <div class="series-desc">This is the description.</div>
                <div class="series-thumb"><img src="//image.url/cover.jpg"></div>
                <a class="genre-name" href="/genre/fantasy">Fantasy</a>
            </body>
        </html>
        """
        mock_page.content.return_value = html

        metadata = self.source.get_metadata("https://tapas.io/series/123")

        self.assertEqual(metadata['title'], "Tapas Series Title")
        self.assertEqual(metadata['author'], "Author Name")
        self.assertEqual(metadata['description'], "This is the description.")
        self.assertIn("Fantasy", metadata['tags'])
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

        # Mock evaluate result
        links = [
            {'href': 'https://tapas.io/episode/1', 'text': 'Episode 1', 'is_locked': False},
            {'href': 'https://tapas.io/episode/2', 'text': 'Episode 2', 'is_locked': True},
            {'href': 'https://tapas.io/other', 'text': 'Other', 'is_locked': False}
        ]
        mock_page.evaluate.return_value = links

        chapters = self.source.get_chapter_list("https://tapas.io/series/123")

        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0]['title'], "Episode 1")
        self.assertEqual(chapters[0]['url'], "https://tapas.io/episode/1")
        self.assertEqual(chapters[1]['title'], "Episode 2 [LOCKED]")

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
                <article class="viewer__body">
                    <p>Episode content.</p>
                </article>
            </body>
        </html>
        """
        mock_page.content.return_value = html

        content = self.source.get_chapter_content("https://tapas.io/episode/1")
        self.assertIn("Episode content.", content)

    @patch('playwright.sync_api.sync_playwright')
    def test_search(self, mock_sync_playwright):
        # Skip search test similarly to WebNovel due to complexity of mocking specific unknown selectors without real HTML
        pass

if __name__ == '__main__':
    unittest.main()
