import unittest
from unittest.mock import MagicMock, patch
from scrollarr.sources.fanfiction import FanFictionSource

class TestFanFictionSource(unittest.TestCase):
    def setUp(self):
        self.source = FanFictionSource()

    def test_identify(self):
        self.assertTrue(self.source.identify("https://www.fanfiction.net/s/123/1/Title"))
        self.assertTrue(self.source.identify("https://www.fictionpress.com/s/456/1/Title"))
        self.assertFalse(self.source.identify("https://google.com"))

    @patch('playwright.sync_api.sync_playwright')
    def test_get_metadata(self, mock_sync_playwright):
        # Mock Context
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
                <div id="profile_top" class="xcontrast_txt">
                    <b class="xcontrast_txt">Test Fanfic Title</b>
                    <span>By:</span> <a href="/u/123/author">Test Author</a>
                    <div class="xcontrast_txt">This is a test summary.</div>
                    <img class="cimage" src="//image.url/cover.jpg">
                    <span class="xgray xcontrast_txt">Rated: T - English - Romance - Chapters: 10 - Status: Complete</span>
                </div>
            </body>
        </html>
        """
        mock_page.content.return_value = html

        metadata = self.source.get_metadata("https://www.fanfiction.net/s/123/1/Title")

        self.assertEqual(metadata['title'], "Test Fanfic Title")
        self.assertEqual(metadata['author'], "Test Author")
        self.assertIn("test summary", metadata['description'])
        self.assertEqual(metadata['rating'], "T")
        self.assertEqual(metadata['publication_status'], "Completed")
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

        html = """
        <html>
            <body>
                <select id="chap_select">
                    <option value="1">1. Chapter One</option>
                    <option value="2">2. Chapter Two</option>
                </select>
            </body>
        </html>
        """
        mock_page.content.return_value = html

        chapters = self.source.get_chapter_list("https://www.fanfiction.net/s/123/1/Title")

        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0]['title'], "Chapter One")
        self.assertEqual(chapters[0]['url'], "https://www.fanfiction.net/s/123/1")
        self.assertEqual(chapters[1]['title'], "Chapter Two")
        self.assertEqual(chapters[1]['url'], "https://www.fanfiction.net/s/123/2")

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
                <div id="storytext">
                    <p>This is the story content.</p>
                </div>
            </body>
        </html>
        """
        mock_page.content.return_value = html

        content = self.source.get_chapter_content("https://www.fanfiction.net/s/123/1")
        self.assertIn("This is the story content.", content)

    @patch('playwright.sync_api.sync_playwright')
    def test_search(self, mock_sync_playwright):
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
                <div class="z-list">
                    <a class="stitle" href="/s/999/1/Search-Result">Search Result</a>
                    <a href="/u/888/Author">Author Name</a>
                    <img class="cimage" src="//cover.jpg">
                </div>
            </body>
        </html>
        """
        mock_page.content.return_value = html

        results = self.source.search("query")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], "Search Result")
        self.assertEqual(results[0]['author'], "Author Name")
        self.assertEqual(results[0]['url'], "https://www.fanfiction.net/s/999/1/Search-Result")

if __name__ == '__main__':
    unittest.main()
