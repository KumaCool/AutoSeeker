import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from boss_zhipin.auth import AuthError, import_cookies, validate_cookies


class AuthServiceTests(unittest.TestCase):
    def test_import_filters_domains_and_sets_mode_0600(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.json"
            destination = root / "secrets" / "cookies.json"
            source.write_text(json.dumps([
                {"name": "zp_at", "value": "token", "domain": ".zhipin.com"},
                {"name": "wt2", "value": "visitor", "domain": "www.zhipin.com"},
                {"name": "other", "value": "secret", "domain": ".example.com"},
            ]), encoding="utf-8")

            count = import_cookies(source, destination)
            payload = json.loads(destination.read_text(encoding="utf-8"))
            mode = destination.stat().st_mode & 0o777

        self.assertEqual(count, 2)
        self.assertEqual({item["name"] for item in payload}, {"zp_at", "wt2"})
        self.assertEqual(mode, 0o600)

    def test_validate_requires_nonempty_zp_at(self):
        with self.assertRaises(AuthError):
            validate_cookies([{"name": "wt2", "value": "visitor", "domain": ".zhipin.com"}])

    def test_check_uses_minimal_single_page_request(self):
        from boss_zhipin import auth

        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"code": 0, "zpData": {"jobList": []}}
        session = Mock()
        session.post.return_value = response

        result = auth.check_cookies({"zp_at": "token"}, session=session)

        self.assertEqual(result, 0)
        session.post.assert_called_once()
        self.assertEqual(session.post.call_args.kwargs["data"]["pageSize"], "1")


if __name__ == "__main__":
    unittest.main()
