import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from auto_seeker.auth import (
    AuthError,
    fetch_user_name,
    import_cookies,
    import_verified_cookies,
    load_cookie_file,
    validate_cookies,
)


class AuthServiceTests(unittest.TestCase):
    def test_import_filters_domains_and_sets_mode_0600(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.json"
            destination = root / "secrets" / "cookies.json"
            source.write_text(
                json.dumps(
                    [
                        {"name": "zp_at", "value": "token", "domain": ".zhipin.com"},
                        {"name": "wt2", "value": "visitor", "domain": "www.zhipin.com"},
                        {"name": "other", "value": "secret", "domain": ".example.com"},
                    ]
                ),
                encoding="utf-8",
            )

            count = import_cookies(source, destination)
            payload = json.loads(destination.read_text(encoding="utf-8"))
            mode = destination.stat().st_mode & 0o777

        self.assertEqual(count, 2)
        self.assertEqual({item["name"] for item in payload}, {"zp_at", "wt2"})
        self.assertEqual(mode, 0o600)

    def test_validate_requires_nonempty_zp_at(self):
        with self.assertRaises(AuthError):
            validate_cookies([{"name": "wt2", "value": "visitor", "domain": ".zhipin.com"}])

    def test_load_cookie_file_falls_back_to_legacy_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy = root / "cookies.json"
            legacy.write_text('{"zp_at": "legacy-token"}', encoding="utf-8")

            cookies = load_cookie_file(root / "var/secrets/cookies.json", legacy)

        self.assertEqual(cookies, {"zp_at": "legacy-token"})

    def test_load_cookie_file_accepts_simplified_name_value_array(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cookies.json"
            path.write_text('[{"name": "zp_at", "value": "token"}]', encoding="utf-8")

            cookies = load_cookie_file(path)

        self.assertEqual(cookies, {"zp_at": "token"})

    def test_load_cookie_file_falls_back_to_configured_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            text_path = root / "var/secrets/cookies.txt"
            text_path.parent.mkdir(parents=True)
            text_path.write_text("zp_at=token; wt2=visitor", encoding="utf-8")

            cookies = load_cookie_file(root / "var/secrets/cookies.json", text_path=text_path)

        self.assertEqual(cookies, {"zp_at": "token", "wt2": "visitor"})

    def test_load_cookie_file_falls_back_to_legacy_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy_text = root / "cookies.txt"
            legacy_text.write_text("zp_at=legacy; wt2=visitor", encoding="utf-8")

            cookies = load_cookie_file(
                root / "var/secrets/cookies.json",
                root / "cookies.json",
                root / "var/secrets/cookies.txt",
                legacy_text,
            )

        self.assertEqual(cookies, {"zp_at": "legacy", "wt2": "visitor"})

    def test_check_uses_minimal_single_page_request(self):
        from auto_seeker import auth

        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"code": 0, "zpData": {"jobList": []}}
        session = Mock()
        session.post.return_value = response

        result = auth.check_cookies({"zp_at": "token"}, session=session)

        self.assertEqual(result, 0)
        session.post.assert_called_once()
        self.assertEqual(session.post.call_args.kwargs["data"]["pageSize"], "1")

    def test_fetch_user_name_reads_nested_base_info(self):
        session = Mock()
        response = Mock()
        response.json.return_value = {"code": 0, "zpData": {"baseInfo": {"name": "Kuma"}}}
        session.get.return_value = response

        name = fetch_user_name({"zp_at": "token"}, session=session)

        self.assertEqual(name, "Kuma")
        session.get.assert_called_once()

    def test_fetch_user_name_rejects_business_error(self):
        session = Mock()
        response = Mock()
        response.json.return_value = {"code": 36, "message": "账户异常"}
        session.get.return_value = response

        with self.assertRaisesRegex(AuthError, "业务码=36"):
            fetch_user_name({"zp_at": "token"}, session=session)

    def test_verified_import_does_not_replace_existing_file_on_profile_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "cookies.json"
            destination.write_text('[{"name":"zp_at","value":"old","domain":".zhipin.com"}]')
            source = json.dumps([{"name": "zp_at", "value": "new", "domain": ".zhipin.com"}]).encode()

            with patch("auto_seeker.auth.fetch_user_name", side_effect=AuthError("业务码=36")):
                with self.assertRaises(AuthError):
                    import_verified_cookies(source, destination)

            self.assertIn('"old"', destination.read_text())

    def test_verified_import_writes_0600_and_returns_name(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "cookies.json"
            source = json.dumps([{"name": "zp_at", "value": "new", "domain": ".zhipin.com"}]).encode()

            with patch("auto_seeker.auth.fetch_user_name", return_value="Kuma"):
                name = import_verified_cookies(source, destination)

            self.assertEqual(name, "Kuma")
            self.assertEqual(destination.stat().st_mode & 0o777, 0o600)
            self.assertIn('"new"', destination.read_text())


if __name__ == "__main__":
    unittest.main()
