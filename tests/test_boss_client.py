import unittest
from unittest.mock import Mock

from auto_seeker.infrastructure.boss_client import BossApiError, BossClient
from auto_seeker.models import SearchCriteria


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

    def test_requests_job_detail_with_list_metadata(self):
        session = Mock()
        response = Mock()
        response.json.return_value = {
            "code": 0,
            "zpData": {"bossInfo": {"bossOnline": False, "activeTimeDesc": "3月内活跃"}},
        }
        session.get.return_value = response
        client = BossClient(session, self.criteria)
        job = Mock(job_id="job-id", security_id="security", lid="search-lid")

        payload = client.request_job_detail(job)

        self.assertEqual(payload["zpData"]["bossInfo"]["activeTimeDesc"], "3月内活跃")
        self.assertEqual(session.get.call_args.kwargs["params"]["securityId"], "security")
        self.assertEqual(session.get.call_args.kwargs["params"]["jobId"], "job-id")
        self.assertEqual(session.get.call_args.kwargs["params"]["lid"], "search-lid")

    def test_security_challenge_is_returned_for_stoken_service(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"code": 37, "zpData": {"seed": "s", "name": "n", "ts": 1}}
        self.session.post.return_value = response

        self.assertEqual(self.client.request_page(1)["code"], 37)


if __name__ == "__main__":
    unittest.main()
