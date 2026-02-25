import unittest
import sys
import os
from unittest.mock import MagicMock
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scrollarr.sources.royalroad import RoyalRoadSource

class TestRoyalRoadAntiScraping(unittest.TestCase):
    def setUp(self):
        self.rr = RoyalRoadSource()
        self.rr.requester = MagicMock()

    def test_remove_hidden_paragraphs_via_style(self):
        html = """
        <html>
        <head>
            <style>
                .cjRandomClass123 {
                    display: none;
                    speak: never;
                }
            </style>
        </head>
        <body>
            <div class="chapter-inner">
                <p>This is real story content.</p>
                <span class="cjRandomClass123">
                    <br>
                    A case of content theft: this narrative is not rightfully on Amazon; if you spot it, report the violation.
                    <br>
                </span>
                <p>More real story content.</p>
            </div>
        </body>
        </html>
        """
        self.rr.requester.get.return_value.text = html
        content = self.rr.get_chapter_content("http://example.com/chapter/1")

        self.assertIn("This is real story content.", content)
        self.assertIn("More real story content.", content)
        self.assertNotIn("A case of content theft", content)
        self.assertNotIn("Amazon", content)

    def test_remove_hidden_paragraphs_multiple_styles(self):
        html = """
        <html>
        <head>
            <style>
                .someOtherClass { color: red; }
            </style>
            <style>
                .cjHiddenClass { display: none; }
            </style>
        </head>
        <body>
            <div class="chapter-inner">
                <p>Real content.</p>
                <div class="cjHiddenClass">Do not read me.</div>
            </div>
        </body>
        </html>
        """
        self.rr.requester.get.return_value.text = html
        content = self.rr.get_chapter_content("http://example.com/chapter/2")
        self.assertNotIn("Do not read me", content)

    def test_preserves_visible_content(self):
        html = """
        <html>
        <head>
            <style>
                .cjHidden { display: none; }
                .cnVisible { display: block; }
            </style>
        </head>
        <body>
            <div class="chapter-inner">
                <p class="cnVisible">I am visible content.</p>
                <p class="cjHidden">I am hidden content.</p>
            </div>
        </body>
        </html>
        """
        self.rr.requester.get.return_value.text = html
        content = self.rr.get_chapter_content("http://example.com/chapter/3")
        self.assertIn("I am visible content", content)
        self.assertNotIn("I am hidden content", content)

if __name__ == '__main__':
    unittest.main()
