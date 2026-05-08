import unittest
from unittest.mock import patch, MagicMock
from scrollarr.sources.discord import DiscordSource

class TestDiscordSource(unittest.TestCase):
    def setUp(self):
        self.source = DiscordSource()
        self.source._get_token = MagicMock(return_value="fake_token")

    def test_identify(self):
        self.assertTrue(self.source.identify("discord://123456789"))
        self.assertFalse(self.source.identify("https://discord.com/channels/123/456"))

    @patch('requests.get')
    def test_get_metadata(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "storyupdates",
            "topic": "Latest chapter epubs"
        }
        mock_get.return_value = mock_response

        meta = self.source.get_metadata("discord://12345")
        self.assertEqual(meta['title'], "#storyupdates")
        self.assertEqual(meta['description'], "Latest chapter epubs")
        self.assertEqual(meta['author'], "Discord Bot")

    @patch('requests.get')
    def test_get_chapter_list(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Simulating Discord returning messages newest first
        mock_response.json.return_value = [
            {
                "id": "1002",
                "timestamp": "2024-10-11T12:00:00+00:00",
                "attachments": [{"filename": "Chapter2.epub", "url": "http://cdn/2"}]
            },
            {
                "id": "1001",
                "timestamp": "2024-10-10T12:00:00+00:00",
                "attachments": [{"filename": "Chapter1.epub", "url": "http://cdn/1"}]
            }
        ]
        mock_get.return_value = mock_response

        chapters = self.source.get_chapter_list("discord://12345")
        
        self.assertEqual(len(chapters), 2)
        # Should be reversed to chronological order
        self.assertEqual(chapters[0]['title'], "Chapter1")
        self.assertEqual(chapters[0]['url'], "discord://12345/1001")
        self.assertEqual(chapters[1]['title'], "Chapter2")
        self.assertEqual(chapters[1]['url'], "discord://12345/1002")

    @patch('requests.get')
    def test_get_chapter_list_with_last_chapter(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": "1003",
                "attachments": [{"filename": "Chapter3.epub", "url": "http://cdn/3"}]
            },
            {
                "id": "1002",
                "attachments": [{"filename": "Chapter2.epub", "url": "http://cdn/2"}]
            }
        ]
        mock_get.return_value = mock_response

        # Pass a last chapter to simulate update checking
        chapters = self.source.get_chapter_list(
            "discord://12345", 
            last_chapter={"url": "discord://12345/1002"}
        )
        
        # It should stop when it sees 1002, so only 1003 is returned
        self.assertEqual(len(chapters), 1)
        self.assertEqual(chapters[0]['title'], "Chapter3")

if __name__ == '__main__':
    unittest.main()
