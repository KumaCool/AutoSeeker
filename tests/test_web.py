import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from auto_seeker.web.app import create_app


class WebHealthTests(unittest.TestCase):
    def test_root_redirects_to_jobs(self):
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(Path(directory) / "autoseeker.sqlite3"))
            response = client.get("/", follow_redirects=False)

        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers["location"], "/jobs")

    def test_health_checks_database_without_network(self):
        with tempfile.TemporaryDirectory() as directory, patch("requests.Session.request") as network:
            client = TestClient(create_app(Path(directory) / "autoseeker.sqlite3"))
            response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "ok"})
        network.assert_not_called()

    def test_static_css_is_served(self):
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(Path(directory) / "autoseeker.sqlite3"))
            response = client.get("/static/app.css")

        self.assertEqual(response.status_code, 200)
        self.assertIn("--accent", response.text)


if __name__ == "__main__":
    unittest.main()
