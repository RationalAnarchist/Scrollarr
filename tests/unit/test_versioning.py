import unittest
import os
import json
from unittest.mock import patch, mock_open
from scrollarr.app import get_app_version
from scrollarr.generate_version import main as generate_version_main

class TestVersioning(unittest.TestCase):
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.read_text")
    def test_get_app_version_txt(self, mock_read_text, mock_exists):
        # Test reading from version.txt
        mock_exists.return_value = True
        mock_read_text.return_value = "0.6.2\n"
        version = get_app_version()
        self.assertEqual(version, "0.6.2")

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    @patch("os.path.exists", return_value=True)
    def test_generate_version_main_branch(self, mock_exists, mock_json_load, mock_file):
        # Test bumping minor version when GITHUB_REF is main
        mock_json_load.return_value = {"major": 0, "minor": 5, "patch": 1}
        
        with patch.dict(os.environ, {"GITHUB_REF": "refs/heads/main"}):
            with patch("sys.argv", ["generate_version.py"]):
                generate_version_main()
                
                # Check that it wrote 0.6.0 to version.txt
                handle = mock_file()
                handle.write.assert_any_call("0.6.0\n")

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    @patch("os.path.exists", return_value=True)
    def test_generate_version_test_branch(self, mock_exists, mock_json_load, mock_file):
        # Test bumping patch version when GITHUB_REF is a PR (e.g. 0.5.9 -> 0.5.10)
        mock_json_load.return_value = {"major": 0, "minor": 5, "patch": 9}
        
        with patch.dict(os.environ, {"GITHUB_REF": "refs/pull/123/merge"}):
            with patch("sys.argv", ["generate_version.py"]):
                generate_version_main()
                
                # Check that it wrote 0.5.10 to version.txt
                handle = mock_file()
                handle.write.assert_any_call("0.5.10\n")
