import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from boss_zhipin.infrastructure.stoken import SecurityChallengeError, StokenService


class StokenServiceTests(unittest.TestCase):
    def test_refresh_uses_single_challenge_and_replaces_four_cookies(self):
        session = Mock()
        session.cookies.__iter__ = Mock(return_value=iter([]))
        service = StokenService(session, "https://www.zhipin.com/web/geek/jobs", Path("cache"))
        service.compute_token = Mock(return_value="token")
        challenge = {"zpData": {"seed": "seed", "name": "abc", "ts": 123}}

        service.refresh(challenge)

        service.compute_token.assert_called_once_with("seed", "abc", 123)
        names = [call.args[0] for call in session.cookies.set.call_args_list]
        self.assertEqual(names, ["__zp_stoken__", "__zp_sseed__", "__zp_sname__", "__zp_sts__"])

    def test_missing_challenge_field_fails(self):
        service = StokenService(Mock(), "page", Path("cache"))
        with self.assertRaises(SecurityChallengeError):
            service.refresh({"zpData": {"seed": "seed"}})


if __name__ == "__main__":
    unittest.main()
