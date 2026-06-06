import unittest
from unittest.mock import MagicMock, patch
from scrollarr.sources.patreon import PatreonSource
from datetime import datetime
import json

class TestPatreonSource(unittest.TestCase):
    def setUp(self):
        self.patreon = PatreonSource()

    def test_identify(self):
        self.assertTrue(self.patreon.identify("https://www.patreon.com/Sleyca"))
        self.assertTrue(self.patreon.identify("https://patreon.com/some_creator"))
        self.assertFalse(self.patreon.identify("https://google.com"))

    @patch('scrollarr.browser_manager.BrowserManager.get_page')
    def test_get_metadata(self, mock_get_page):
        mock_page = MagicMock()
        mock_get_page.return_value = mock_page

        html = """
        <html>
            <head>
                <meta property="og:title" content="Sleyca | Patreon">
                <meta property="og:description" content="Creating web novel fictions.">
                <meta property="og:image" content="https://patreon-media/avatar.png">
            </head>
            <body>
            </body>
        </html>
        """
        mock_page.content.return_value = html

        metadata = self.patreon.get_metadata("https://www.patreon.com/Sleyca")

        self.assertEqual(metadata['title'], "Sleyca")
        self.assertEqual(metadata['author'], "Sleyca")
        self.assertEqual(metadata['description'], "Creating web novel fictions.")
        self.assertEqual(metadata['cover_url'], "https://patreon-media/avatar.png")

    @patch('scrollarr.browser_manager.BrowserManager.get_page')
    def test_get_chapter_list(self, mock_get_page):
        mock_page = MagicMock()
        mock_get_page.return_value = mock_page

        # First return html containing campaign ID, then mock evaluate response for API
        html = "<html><body>patreon-media/p/campaign/10546888</body></html>"
        mock_page.content.return_value = html

        def mock_evaluate(script, *args):
            return {
                'data': [
                    {
                        'id': '111',
                        'attributes': {
                            'title': 'Chapter 1',
                            'published_at': '2026-06-01T05:00:00.000+00:00',
                            'current_user_can_view': True
                        }
                    },
                    {
                        'id': '222',
                        'attributes': {
                            'title': 'Chapter 2',
                            'published_at': '2026-06-02T05:00:00.000+00:00',
                            'current_user_can_view': False
                        }
                    }
                ],
                'links': {
                    'next': None
                }
            }

        mock_page.evaluate.side_effect = mock_evaluate

        chapters = self.patreon.get_chapter_list("https://www.patreon.com/Sleyca")

        self.assertEqual(len(chapters), 2)
        # Check order sorting and properties
        self.assertEqual(chapters[0]['title'], "Chapter 1")
        self.assertTrue(chapters[0]['has_access'])
        self.assertEqual(chapters[1]['title'], "Chapter 2")
        self.assertFalse(chapters[1]['has_access'])
        self.assertEqual(chapters[0]['published_date'].year, 2026)

    @patch('scrollarr.browser_manager.BrowserManager.get_page')
    def test_get_chapter_content_unlocked_html(self, mock_get_page):
        mock_page = MagicMock()
        mock_get_page.return_value = mock_page

        mock_page.evaluate.return_value = {
            'data': {
                'attributes': {
                    'current_user_can_view': True,
                    'content': '<p>Unlocked HTML content</p>'
                }
            },
            'included': [
                {
                    'type': 'attachment',
                    'attributes': {
                        'name': 'chapter1.epub',
                        'url': 'https://patreon-media/chapter1.epub'
                    }
                }
            ]
        }

        content = self.patreon.get_chapter_content("https://www.patreon.com/posts/111")
        self.assertIn("Unlocked HTML content", content)
        self.assertIn("chapter1.epub", content)

    @patch('scrollarr.browser_manager.BrowserManager.get_page')
    def test_get_chapter_content_unlocked_prosemirror(self, mock_get_page):
        mock_page = MagicMock()
        mock_get_page.return_value = mock_page

        prosemirror_json = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "Hello world from <<ProseMirror>>"
                        }
                    ]
                }
            ]
        }

        mock_page.evaluate.return_value = {
            'data': {
                'attributes': {
                    'current_user_can_view': True,
                    'content_json_string': json.dumps(prosemirror_json)
                }
            }
        }

        content = self.patreon.get_chapter_content("https://www.patreon.com/posts/111")
        self.assertIn("<p>Hello world from &lt;&lt;ProseMirror&gt;&gt;</p>", content)

    @patch('scrollarr.browser_manager.BrowserManager.get_page')
    def test_get_chapter_content_locked(self, mock_get_page):
        mock_page = MagicMock()
        mock_get_page.return_value = mock_page

        mock_page.evaluate.return_value = {
            'data': {
                'attributes': {
                    'current_user_can_view': False
                }
            }
        }

        with self.assertRaises(Exception) as ctx:
            self.patreon.get_chapter_content("https://www.patreon.com/posts/222")
        self.assertIn("Patreon post is locked", str(ctx.exception))

if __name__ == '__main__':
    unittest.main()
