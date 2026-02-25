import unittest
from unittest.mock import MagicMock, patch
from scrollarr.sources.kemono import KemonoSource
from datetime import datetime

class TestKemonoTags(unittest.TestCase):
    def setUp(self):
        self.kemono = KemonoSource()

    @patch('playwright.sync_api.sync_playwright')
    def test_get_chapter_list_with_tags(self, mock_sync_playwright):
        # Mock Playwright setup
        mock_playwright_context_manager = MagicMock()
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()

        mock_sync_playwright.return_value = mock_playwright_context_manager
        mock_playwright_context_manager.__enter__.return_value = mock_playwright
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        # Mock API Responses via page.evaluate
        def mock_evaluate(script, *args):
            # 1. Fetch tags
            if "/tags" in script:
                return {'success': True, 'data': [{'tag': 'Tag1'}, {'tag': 'Tag 2'}]}

            # 2. Build Tag Map (Promise.all)
            # The script contains "async (tags) => {"
            if "async (tags) => {" in script:
                # args[0] is the chunk of tags
                chunk = args[0]
                results = {}
                for tag in chunk:
                    if tag == 'Tag1':
                        results[tag] = ['100']
                    elif tag == 'Tag 2':
                        results[tag] = ['100']
                    else:
                        results[tag] = []
                return results

            # 3. Fetch Posts page 0
            if "/posts?o=0" in script:
                return {'success': True, 'data': [
                    {'id': '100', 'title': 'Post with Tags', 'published': '2023-01-01T00:00:00'},
                    {'id': '101', 'title': 'Post without Tags', 'published': '2023-01-02T00:00:00'}
                ]}

            # 4. Fetch Posts page 50 (end)
            if "/posts?o=50" in script:
                return {'success': True, 'data': []}

            return {'success': False, 'error': 'Unknown script'}

        mock_page.evaluate.side_effect = mock_evaluate

        chapters = self.kemono.get_chapter_list("https://kemono.su/fanbox/user/123")

        self.assertEqual(len(chapters), 2)

        # Note: Sorted by date ascending
        # Post with Tags (2023-01-01) comes first
        self.assertEqual(chapters[0]['title'], "Post with Tags")
        self.assertIn('tags', chapters[0])
        # Since 'Tag1' and 'Tag 2' both map to '100'
        self.assertEqual(set(chapters[0]['tags']), {'Tag1', 'Tag 2'})

        # Post without Tags (2023-01-02) comes second
        self.assertEqual(chapters[1]['title'], "Post without Tags")
        self.assertIn('tags', chapters[1])
        self.assertEqual(chapters[1]['tags'], [])

if __name__ == '__main__':
    unittest.main()
