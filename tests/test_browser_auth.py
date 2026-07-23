import json
import tempfile
import unittest
from pathlib import Path

from auto_seeker import browser_auth


class BrowserAuthTests(unittest.TestCase):
    def test_login_requires_nonempty_zp_at(self):
        self.assertFalse(browser_auth.is_logged_in([]))
        self.assertFalse(browser_auth.is_logged_in([{"name": "zp_at", "value": ""}]))
        self.assertTrue(browser_auth.is_logged_in([{"name": "zp_at", "value": "token"}]))

    def test_only_zhipin_cookies_are_saved(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "cookies.json"
            count = browser_auth.save_cookies(
                [
                    {"name": "zp_at", "value": "token", "domain": ".zhipin.com"},
                    {"name": "wt2", "value": "visitor", "domain": "www.zhipin.com"},
                    {"name": "other", "value": "secret", "domain": ".example.com"},
                ],
                destination,
            )
            payload = json.loads(destination.read_text(encoding="utf-8"))

            self.assertEqual(count, 2)
            self.assertEqual({item["name"] for item in payload}, {"zp_at", "wt2"})
            self.assertEqual(destination.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
