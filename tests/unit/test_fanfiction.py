import unittest
from unittest.mock import MagicMock, patch
from scrollarr.sources.fanfiction import FanFictionSource
import io
import zipfile

class TestFanFictionSource(unittest.TestCase):
    def setUp(self):
        self.source = FanFictionSource()

    def test_identify(self):
        self.assertTrue(self.source.identify("https://www.fanfiction.net/s/123/1/Title"))
        self.assertTrue(self.source.identify("https://www.fictionpress.com/s/456/1/Title"))
        self.assertFalse(self.source.identify("https://google.com"))

    @patch('requests.get')
    def test_get_metadata(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "meta": {
                "title": "Test Fanfic Title",
                "author": "Test Author",
                "description": "<p>test summary.</p>",
                "status": "complete",
                "rawExtendedMeta": {
                    "rated": "T",
                    "language": "English"
                }
            }
        }
        mock_get.return_value = mock_response

        metadata = self.source.get_metadata("https://www.fanfiction.net/s/123/1/Title")

        self.assertEqual(metadata['title'], "Test Fanfic Title")
        self.assertEqual(metadata['author'], "Test Author")
        self.assertIn("test summary", metadata['description'])
        self.assertEqual(metadata['rating'], "T")
        self.assertEqual(metadata['publication_status'], "Completed")

    @patch('requests.get')
    def test_get_chapter_list(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "meta": {
                "chapters": 2,
                "created": "2020-01-01T12:00:00",
                "updated": "2020-01-02T12:00:00"
            }
        }
        mock_get.return_value = mock_response

        chapters = self.source.get_chapter_list("https://www.fanfiction.net/s/123/1/Title")

        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0]['title'], "Chapter 1")
        self.assertEqual(chapters[0]['url'], "https://www.fanfiction.net/s/123/1")
        self.assertEqual(chapters[1]['title'], "Chapter 2")
        self.assertEqual(chapters[1]['url'], "https://www.fanfiction.net/s/123/2")

    @patch('requests.get')
    def test_get_chapter_content(self, mock_get):
        mock_meta_response = MagicMock()
        mock_meta_response.status_code = 200
        mock_meta_response.json.return_value = {
            "html_url": "/epub/123.zip"
        }
        
        mock_zip_response = MagicMock()
        mock_zip_response.status_code = 200
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            html_content = "<html><body><h2>Chapter 1</h2><p>This is the story content.</p></body></html>"
            zf.writestr("story.html", html_content)
        mock_zip_response.content = zip_buffer.getvalue()

        def get_side_effect(url, **kwargs):
            if "fichub.net/api/v0/epub" in url:
                return mock_meta_response
            elif "fichub.net/epub/" in url:
                return mock_zip_response
            return MagicMock(status_code=404)
            
        mock_get.side_effect = get_side_effect

        content = self.source.get_chapter_content("https://www.fanfiction.net/s/123/1")
        self.assertIn("This is the story content.", content)

    @patch('requests.post')
    def test_search(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        html = """
        <html>
            <body>
                <table>
                    <tr class="result-row">
                        <td><a class="result-url" href="https://www.fanfiction.net/s/999/1/Search-Result">Search Result</a></td>
                    </tr>
                    <tr class="result-snippet">
                        <td class="result-snippet">By: Author Name. Genre: Fantasy. Words: 10k</td>
                    </tr>
                </table>
            </body>
        </html>
        """
        mock_response.text = html
        mock_post.return_value = mock_response

        results = self.source.search("query")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], "Search Result")
        self.assertEqual(results[0]['author'], "Author Name")
        self.assertEqual(results[0]['url'], "https://www.fanfiction.net/s/999/1")

    @patch('requests.get')
    def test_get_chapter_content_chap_id(self, mock_get):
        self.source._fichub_cache.clear()
        mock_meta_response = MagicMock()
        mock_meta_response.status_code = 200
        mock_meta_response.json.return_value = {"html_url": "/epub/124.zip"}
        
        mock_zip_response = MagicMock()
        mock_zip_response.status_code = 200
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            html_content = '<html><body><div id="chap_1"><h2>Custom Title 1</h2><p>Chapter 1 text</p></div><div id="chap_2"><h2>Custom Title 2</h2><p>Chapter 2 text</p></div></body></html>'
            zf.writestr("story.html", html_content)
        mock_zip_response.content = zip_buffer.getvalue()

        def get_side_effect(url, **kwargs):
            if "fichub.net/api/v0/epub" in url:
                return mock_meta_response
            elif "fichub.net/epub/" in url:
                return mock_zip_response
            return MagicMock(status_code=404)
            
        mock_get.side_effect = get_side_effect

        content1 = self.source.get_chapter_content("https://www.fanfiction.net/s/124/1")
        self.source._fichub_cache.clear() # clear cache to test same URL but different index
        content2 = self.source.get_chapter_content("https://www.fanfiction.net/s/124/2")
        self.assertIn("Chapter 1 text", content1)
        self.assertIn("Chapter 2 text", content2)

    @patch('requests.get')
    def test_get_chapter_content_h2_custom_title(self, mock_get):
        self.source._fichub_cache.clear()
        mock_meta_response = MagicMock()
        mock_meta_response.status_code = 200
        mock_meta_response.json.return_value = {"html_url": "/epub/125.zip"}
        
        mock_zip_response = MagicMock()
        mock_zip_response.status_code = 200
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            html_content = '<html><body><h1>Book Title</h1><h2>by Test Author</h2><h2>Literally Incredible</h2><p>Chapter 1 body</p><h2>Dissemination</h2><p>Chapter 2 body</p></body></html>'
            zf.writestr("story.html", html_content)
        mock_zip_response.content = zip_buffer.getvalue()

        def get_side_effect(url, **kwargs):
            if "fichub.net/api/v0/epub" in url:
                return mock_meta_response
            elif "fichub.net/epub/" in url:
                return mock_zip_response
            return MagicMock(status_code=404)
            
        mock_get.side_effect = get_side_effect

        content1 = self.source.get_chapter_content("https://www.fanfiction.net/s/125/1")
        self.source._fichub_cache.clear()
        content2 = self.source.get_chapter_content("https://www.fanfiction.net/s/125/2")
        self.assertIn("Chapter 1 body", content1)
        self.assertIn("Chapter 2 body", content2)

if __name__ == '__main__':
    unittest.main()
