import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from auto_seeker.application.collect_jobs import CollectionError, collect_jobs
from auto_seeker.infrastructure.sqlite_repository import SQLiteJobRepository
from auto_seeker.models import SearchCriteria

PAYLOAD = {
    "code": 0,
    "zpData": {
        "jobList": [
            {
                "salaryDesc": "15-20K",
                "jobExperience": "1-3年",
                "encryptJobId": "id-1",
                "jobName": "前端",
                "brandName": "公司",
                "cityName": "武汉",
            }
        ]
    },
}


class SQLiteCollectionIntegrationTests(unittest.TestCase):
    def test_successful_collection_completes_run(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteJobRepository(Path(directory) / "autoseeker.sqlite3")
            client = Mock()
            client.request_page.return_value = PAYLOAD
            criteria = SearchCriteria("前端", "101200100", 15, 3)

            result = collect_jobs(client, Mock(), repository, criteria, 1, 1, sleep=lambda _: None)
            run = repository.get_run(result.run_id)

            self.assertEqual(result.pages_completed, 1)
            self.assertEqual(result.matched_count, 1)
            self.assertEqual(result.new_count, 1)
            self.assertEqual(run["status"], "completed")
            self.assertEqual(repository.count_jobs(), 1)

    def test_failure_marks_partial_run_after_saving_jobs(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteJobRepository(Path(directory) / "autoseeker.sqlite3")
            client = Mock()
            client.request_page.side_effect = [PAYLOAD, RuntimeError("network")]
            criteria = SearchCriteria("前端", "101200100", 15, 3)

            with self.assertRaises(CollectionError) as captured:
                collect_jobs(client, Mock(), repository, criteria, 1, 2, sleep=lambda _: None)

            run = repository.get_run(captured.exception.result.run_id)
            self.assertEqual(run["status"], "partial")
            self.assertEqual(run["pages_completed"], 1)
            self.assertEqual(run["matched_count"], 1)
            self.assertEqual(repository.count_jobs(), 1)

    def test_storage_failure_marks_run_failed(self):
        repository = Mock()
        repository.begin_run.return_value = 9
        repository.save_jobs.side_effect = RuntimeError("disk full")
        client = Mock()
        client.request_page.return_value = PAYLOAD
        criteria = SearchCriteria("前端", "101200100", 15, 3)

        with self.assertRaises(CollectionError) as captured:
            collect_jobs(client, Mock(), repository, criteria, 1, 1, sleep=lambda _: None)

        self.assertIsNotNone(captured.exception.result)
        self.assertEqual(captured.exception.result.run_id, 9)
        repository.fail_run.assert_called_once_with(
            9,
            pages_completed=1,
            matched_count=1,
            error=repository.save_jobs.side_effect,
            partial=False,
        )


if __name__ == "__main__":
    unittest.main()
