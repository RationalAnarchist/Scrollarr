import unittest
from fastapi.testclient import TestClient
from scrollarr.app import app
from scrollarr.config import config_manager

class TestApiDocs(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

        # Override config to disable auth
        self.original_config = config_manager.config.copy()
        config_manager.config['auth_method'] = 'None'
        config_manager.config['setup_complete'] = True

    def tearDown(self):
        # Restore config
        config_manager.config = self.original_config

    def test_api_docs_endpoint(self):
        response = self.client.get("/api-docs")
        self.assertEqual(response.status_code, 200)
        self.assertIn("API Documentation", response.text)
        self.assertIn("Interactive Documentation", response.text)
        self.assertIn("Open Swagger UI", response.text)

if __name__ == '__main__':
    unittest.main()
