import unittest
from unittest.mock import MagicMock, patch, ANY
from datetime import datetime, timedelta
import sys
import os

# Add repo root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Import sources
from scrollarr.sources.fanfiction import FanFictionSource
from scrollarr.sources.wattpad import WattpadSource
from scrollarr.sources.webnovel import WebNovelSource
from scrollarr.sources.inkitt import InkittSource
from scrollarr.sources.tapas import TapasSource

class TestSourceDateParsing(unittest.TestCase):

    @patch('scrollarr.sources.fanfiction.FanFictionSource._get_playwright')
    def test_fanfiction_date_parsing(self, mock_get_playwright):
        # FanFiction source logic relies on BS4 scraping in get_chapter_list AFTER playwright navigation
        # We need to mock the browser page content
        source = FanFictionSource()

        # Create mocks
        mock_p = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()

        mock_get_playwright.return_value.__enter__.return_value = mock_p
        mock_p.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        # HTML content with timestamps in profile_top
        html_content = """
        <html>
        <body>
            <div id='profile_top'>
                Updated: <span data-xutime='1672617600'>Jan 2, 2023</span>
                Published: <span data-xutime='1672531200'>Jan 1, 2023</span>
            </div>
            <select id='chap_select'>
                <option value='1'>Chapter 1</option>
                <option value='2'>Chapter 2</option>
            </select>
        </body>
        </html>
        """
        mock_page.content.return_value = html_content

        # Call method
        chapters = source.get_chapter_list("https://www.fanfiction.net/s/123/1/")

        # Assertions
        self.assertEqual(len(chapters), 2)
        # First chapter should have Published date (1672531200 -> 2023-01-01)
        self.assertEqual(chapters[0]['published_date'], datetime.fromtimestamp(1672531200))
        # Last chapter should have Updated date (1672617600 -> 2023-01-02)
        self.assertEqual(chapters[1]['published_date'], datetime.fromtimestamp(1672617600))

    @patch('scrollarr.sources.webnovel.WebNovelSource._get_playwright')
    def test_webnovel_date_parsing(self, mock_get_playwright):
        source = WebNovelSource()

        mock_p = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()

        mock_get_playwright.return_value.__enter__.return_value = mock_p
        mock_p.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        # WebNovel uses page.evaluate to extract data including time
        # We mock the return of page.evaluate

        # Mocking the return value of the HREF extraction script
        mock_page.evaluate.return_value = [
            {
                'href': 'https://www.webnovel.com/book/123/1',
                'text': 'Chapter 1',
                'is_locked': False,
                'time': 'Jan 01, 2024'
            },
            {
                'href': 'https://www.webnovel.com/book/123/2',
                'text': 'Chapter 2',
                'is_locked': False,
                'time': '2 hours ago'
            }
        ]

        chapters = source.get_chapter_list("https://www.webnovel.com/book/123")

        self.assertEqual(len(chapters), 2)

        # Chapter 1: Jan 01, 2024
        self.assertEqual(chapters[0]['published_date'].year, 2024)
        self.assertEqual(chapters[0]['published_date'].month, 1)
        self.assertEqual(chapters[0]['published_date'].day, 1)

        # Chapter 2: 2 hours ago
        # We check roughly (within seconds/minute)
        now = datetime.now()
        expected = now - timedelta(hours=2)
        diff = abs((chapters[1]['published_date'] - expected).total_seconds())
        self.assertLess(diff, 60) # Allow 1 min variance

    @patch('scrollarr.sources.tapas.TapasSource._get_playwright')
    def test_tapas_date_parsing(self, mock_get_playwright):
        source = TapasSource()

        mock_p = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()

        mock_get_playwright.return_value.__enter__.return_value = mock_p
        mock_p.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        # Tapas uses page.evaluate
        mock_page.evaluate.side_effect = [
            None, # Scroll result (ignore)
            None,
            None,
            None,
            None,
            [ # HREF result
                {
                    'href': 'https://tapas.io/episode/1',
                    'text': 'Ep 1',
                    'is_locked': False,
                    'date': 'Jan 01, 2024'
                }
            ]
        ]

        chapters = source.get_chapter_list("https://tapas.io/series/123")

        self.assertEqual(len(chapters), 1)
        self.assertEqual(chapters[0]['published_date'].year, 2024)
        self.assertEqual(chapters[0]['published_date'].month, 1)
        self.assertEqual(chapters[0]['published_date'].day, 1)

    @patch('scrollarr.sources.wattpad.WattpadSource._get_playwright')
    def test_wattpad_date_parsing(self, mock_get_playwright):
        source = WattpadSource()

        mock_p = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()

        mock_get_playwright.return_value.__enter__.return_value = mock_p
        mock_p.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        # Wattpad checks window.preloaded first
        # We simulate finding data
        mock_page.evaluate.return_value = [
            {
                'id': '123',
                'title': 'Chapter 1',
                'url': 'https://www.wattpad.com/123',
                'datePublished': '2024-01-01T12:00:00Z'
            }
        ]

        chapters = source.get_chapter_list("https://www.wattpad.com/story/123")

        self.assertEqual(len(chapters), 1)
        self.assertEqual(chapters[0]['published_date'].year, 2024)
        self.assertEqual(chapters[0]['published_date'].month, 1)
        self.assertEqual(chapters[0]['published_date'].day, 1)
        # Ensure UTC handling (Z -> +00:00)
        self.assertEqual(chapters[0]['published_date'].tzinfo.utcoffset(None), timedelta(0))

    @patch('scrollarr.sources.inkitt.InkittSource._get_playwright')
    def test_inkitt_date_parsing(self, mock_get_playwright):
        source = InkittSource()

        mock_p = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()

        mock_get_playwright.return_value.__enter__.return_value = mock_p
        mock_p.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        # Inkitt relies on BS4 scraping after navigation
        # The chapter_list selector in InkittSource is: .chapter-list-item a, li.chapter a
        # Our mock content matches li.chapter a
        html_content = """
        <html>
        <body>
            <ul>
                <li class="chapter">
                    <a href="/stories/123/chapters/1">Chapter 1</a>
                    <span class="date">2024-01-01</span>
                </li>
            </ul>
        </body>
        </html>
        """
        mock_page.content.return_value = html_content
        # evaluate for reader TOC fallback
        mock_page.evaluate.return_value = []

        chapters = source.get_chapter_list("https://www.inkitt.com/stories/123")

        self.assertEqual(len(chapters), 1)
        self.assertEqual(chapters[0]['published_date'].year, 2024)
        self.assertEqual(chapters[0]['published_date'].month, 1)
        self.assertEqual(chapters[0]['published_date'].day, 1)

if __name__ == '__main__':
    unittest.main()
