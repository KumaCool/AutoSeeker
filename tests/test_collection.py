import unittest
from unittest.mock import Mock

from auto_seeker.application.collect_jobs import CollectionError, collect_jobs
from auto_seeker.models import SearchCriteria


class CollectionTests(unittest.TestCase):
    def test_code_37_refreshes_once_then_collects(self):
        client = Mock()
        client.request_page.side_effect = [
            {"code": 37, "zpData": {"seed": "s", "name": "n", "ts": 1}},
            {"code": 0, "zpData": {"jobList": []}},
        ]
        stoken = Mock()
        repository = Mock()
        repository.save.return_value = 0
        criteria = SearchCriteria("前端", "101200100", 15, 3)

        result = collect_jobs(client, stoken, repository, criteria, 1, 1, sleep=lambda _: None)

        stoken.refresh.assert_called_once()
        self.assertEqual(result.pages_completed, 1)
        self.assertEqual(client.request_page.call_count, 2)

    def test_second_code_37_fails_without_looping(self):
        challenge = {"code": 37, "zpData": {"seed": "s", "name": "n", "ts": 1}}
        client = Mock()
        client.request_page.side_effect = [challenge, challenge]
        criteria = SearchCriteria("前端", "101200100", 15, 3)

        with self.assertRaises(CollectionError):
            collect_jobs(client, Mock(), Mock(), criteria, 1, 1, sleep=lambda _: None)

        self.assertEqual(client.request_page.call_count, 2)

    def test_partial_results_are_saved_before_failure(self):
        payload = {
            "code": 0,
            "zpData": {
                "jobList": [
                    {
                        "salaryDesc": "15-20K",
                        "jobExperience": "1-3年",
                        "encryptJobId": "id",
                        "jobName": "前端",
                        "brandName": "公司",
                        "cityName": "武汉",
                    }
                ]
            },
        }
        client = Mock()
        client.request_page.side_effect = [payload, RuntimeError("network")]
        repository = Mock()
        repository.begin_run.return_value = 7
        repository.save_jobs.return_value = 1
        criteria = SearchCriteria("前端", "101200100", 15, 3)

        with self.assertRaises(CollectionError):
            collect_jobs(client, Mock(), repository, criteria, 1, 2, sleep=lambda _: None)

        repository.save_jobs.assert_called_once()
        self.assertEqual(repository.save_jobs.call_args.args[0], 7)
        self.assertEqual(len(repository.save_jobs.call_args.args[1]), 1)
        repository.fail_run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
