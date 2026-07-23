import unittest
from unittest.mock import Mock

from boss_zhipin.infrastructure.boss_client import BossApiError, BossClient
from boss_zhipin.models import SearchCriteria


class BossClientTests(unittest.TestCase):
    def setUp(self):
        self.session = Mock()
        self.criteria = SearchCriteria("前端", "101200100", 15, 3)
        self.client = BossClient(self.session, self.criteria, page_size=30, timeout=12)

    def test_request_page_posts_expected_contract(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"code": 0, "zpData": {"jobList": []}}
        self.session.post.return_value = response

        payload = self.client.request_page(2)

        self.assertEqual(payload["code"], 0)
        call = self.session.post.call_args
        self.assertEqual(call.kwargs["data"]["page"], "2")
        self.assertEqual(call.kwargs["data"]["pageSize"], "30")
        self.assertEqual(call.kwargs["timeout"], 12)

    def test_unknown_business_code_raises_protocol_error(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"code": 5001, "message": "changed"}
        self.session.post.return_value = response

        with self.assertRaises(BossApiError):
            self.client.request_page(1)

    def test_security_challenge_is_returned_for_stoken_service(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"code": 37, "zpData": {"seed": "s", "name": "n", "ts": 1}}
        self.session.post.return_value = response

        self.assertEqual(self.client.request_page(1)["code"], 37)


if __name__ == "__main__":
    unittest.main()
