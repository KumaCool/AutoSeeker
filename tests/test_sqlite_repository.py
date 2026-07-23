import sqlite3
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from auto_seeker.infrastructure.sqlite_repository import SQLiteJobRepository


class SQLiteSchemaTests(unittest.TestCase):
    def test_initializes_schema_pragmas_and_indexes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data" / "autoseeker.sqlite3"
            repository = SQLiteJobRepository(path)

            with repository.connect() as connection:
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                indexes = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='index'")}
                journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
                busy_timeout = connection.execute("PRAGMA busy_timeout").fetchone()[0]
                foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()[0]

            self.assertEqual(tables, {"jobs", "collection_runs", "sqlite_sequence"})
            self.assertTrue(
                {"idx_jobs_last_seen", "idx_jobs_salary_low", "idx_jobs_first_run", "idx_jobs_last_run"}.issubset(
                    indexes
                )
            )
            self.assertEqual(journal_mode, "wal")
            self.assertEqual(busy_timeout, 5000)
            self.assertEqual(foreign_keys, 1)
            self.assertTrue(path.is_file())

    def test_empty_database_does_not_read_legacy_excel(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "autoseeker.sqlite3"
            SQLiteJobRepository(path)
            with sqlite3.connect(path) as connection:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], 0)


class CollectionRunTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.repository = SQLiteJobRepository(Path(self.directory.name) / "autoseeker.sqlite3")

    def tearDown(self):
        self.directory.cleanup()

    def test_completed_run_records_counts_and_timestamps(self):
        run_id = self.repository.begin_run(pages_requested=5)
        self.repository.complete_run(run_id, pages_completed=5, matched_count=12, new_count=3)

        run = self.repository.get_run(run_id)

        self.assertEqual(run["status"], "completed")
        self.assertEqual(run["pages_requested"], 5)
        self.assertEqual(run["pages_completed"], 5)
        self.assertEqual(run["matched_count"], 12)
        self.assertEqual(run["new_count"], 3)
        self.assertIsNotNone(run["finished_at"])
        datetime.fromisoformat(run["started_at"])
        datetime.fromisoformat(run["finished_at"])

    def test_failure_status_depends_on_partial_results(self):
        partial_id = self.repository.begin_run(pages_requested=5)
        failed_id = self.repository.begin_run(pages_requested=5)

        self.repository.fail_run(
            partial_id, pages_completed=2, matched_count=4, error=RuntimeError("network"), partial=True
        )
        self.repository.fail_run(
            failed_id, pages_completed=0, matched_count=0, error=RuntimeError("network"), partial=False
        )

        self.assertEqual(self.repository.get_run(partial_id)["status"], "partial")
        self.assertEqual(self.repository.get_run(failed_id)["status"], "failed")

    def test_failure_message_redacts_known_secrets(self):
        run_id = self.repository.begin_run(pages_requested=1)
        error = RuntimeError("request failed zp_at=secret-value __zp_stoken__=token-value")

        self.repository.fail_run(run_id, pages_completed=0, matched_count=0, error=error, partial=False)
        run = self.repository.get_run(run_id)

        self.assertEqual(run["error_type"], "RuntimeError")
        self.assertNotIn("secret-value", run["error_message"])
        self.assertNotIn("token-value", run["error_message"])
        self.assertIn("<redacted>", run["error_message"])


if __name__ == "__main__":
    unittest.main()
