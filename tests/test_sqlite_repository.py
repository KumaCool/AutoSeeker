import sqlite3
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
