import unittest
from bs4 import BeautifulSoup
from scrollarr.core_logic import BaseSource

class MockSource(BaseSource):
    def identify(self, url): return False
    def get_metadata(self, url): return {}
    def get_chapter_list(self, url, **kwargs): return []
    def get_chapter_content(self, url): return ""
    def search(self, query): return []

class TestHiddenElements(unittest.TestCase):
    def setUp(self):
        self.source = MockSource()

    def test_remove_hidden_classes(self):
        html = """
        <html>
        <head>
            <style>
                .hidden-text { display: none; }
                .other-class { color: red; }
                .complex-hidden { font-weight: bold; display: none; color: blue; }
            </style>
        </head>
        <body>
            <div class="content">
                <p>Visible text.</p>
                <p class="hidden-text">Hidden text by class.</p>
                <p class="complex-hidden">Hidden text by complex class.</p>
                <div class="other-class">Visible red text.</div>
            </div>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        content_div = soup.select_one('.content')

        self.source.remove_hidden_elements(soup, content_div)

        self.assertIsNone(content_div.find(class_="hidden-text"))
        self.assertIsNone(content_div.find(class_="complex-hidden"))
        self.assertIsNotNone(content_div.find(class_="other-class"))
        self.assertIn("Visible text", content_div.get_text())
        self.assertNotIn("Hidden text", content_div.get_text())

    def test_remove_inline_style(self):
        html = """
        <div class="content">
            <p style="display: none">Hidden inline.</p>
            <p style="display:none">Hidden inline compact.</p>
            <p style="color: red; display: none;">Hidden inline complex.</p>
            <p>Visible.</p>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        content_div = soup.select_one('.content')

        self.source.remove_hidden_elements(soup, content_div)

        self.assertEqual(len(content_div.find_all('p')), 1)
        self.assertIn("Visible", content_div.get_text())
        self.assertNotIn("Hidden", content_div.get_text())

if __name__ == '__main__':
    unittest.main()
