import re
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from auto_seeker.models import Job

SCHEMA = """
CREATE TABLE IF NOT EXISTS collection_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL CHECK(status IN ('running', 'completed', 'partial', 'failed')),
    pages_requested INTEGER NOT NULL,
    pages_completed INTEGER NOT NULL DEFAULT 0,
    matched_count INTEGER NOT NULL DEFAULT 0,
    new_count INTEGER NOT NULL DEFAULT 0,
    error_type TEXT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    job_name TEXT NOT NULL,
    company TEXT NOT NULL,
    salary TEXT NOT NULL,
    salary_low REAL NOT NULL,
    salary_high REAL NOT NULL,
    experience TEXT NOT NULL,
    degree TEXT NOT NULL,
    location TEXT NOT NULL,
    boss TEXT NOT NULL,
    skills TEXT NOT NULL,
    url TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    first_seen_run_id INTEGER NOT NULL REFERENCES collection_runs(id),
    last_seen_run_id INTEGER NOT NULL REFERENCES collection_runs(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_last_seen ON jobs(last_seen_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_salary_low ON jobs(salary_low DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_first_run ON jobs(first_seen_run_id);
CREATE INDEX IF NOT EXISTS idx_jobs_last_run ON jobs(last_seen_run_id);
"""


class SQLiteJobRepository:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=5000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _now():
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _redact_error(error):
        message = str(error)
        for name in ("zp_at", "wt2", "__zp_stoken__", "__zp_sseed__", "__zp_sname__"):
            message = re.sub(rf"({re.escape(name)}\s*[=:]\s*)[^\s,;]+", r"\1<redacted>", message)
        return message

    def begin_run(self, pages_requested):
        with self.connect() as connection:
            cursor = connection.execute(
                "INSERT INTO collection_runs(started_at, status, pages_requested) VALUES (?, 'running', ?)",
                (self._now(), pages_requested),
            )
            return cursor.lastrowid

    def complete_run(self, run_id, *, pages_completed, matched_count, new_count):
        with self.connect() as connection:
            connection.execute(
                """UPDATE collection_runs
                   SET finished_at=?, status='completed', pages_completed=?, matched_count=?, new_count=?
                   WHERE id=?""",
                (self._now(), pages_completed, matched_count, new_count, run_id),
            )

    def fail_run(self, run_id, *, pages_completed, matched_count, error, partial):
        with self.connect() as connection:
            connection.execute(
                """UPDATE collection_runs
                   SET finished_at=?, status=?, pages_completed=?, matched_count=?,
                       error_type=?, error_message=?
                   WHERE id=?""",
                (
                    self._now(),
                    "partial" if partial else "failed",
                    pages_completed,
                    matched_count,
                    type(error).__name__,
                    self._redact_error(error),
                    run_id,
                ),
            )

    def get_run(self, run_id):
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM collection_runs WHERE id=?", (run_id,)).fetchone()
        return dict(row) if row else None

    def save_jobs(self, run_id, jobs):
        unique = {}
        for value in jobs:
            item = value if isinstance(value, Job) else Job(**value)
            if not item.job_id:
                raise ValueError("job_id 不能为空")
            unique[item.job_id] = item

        new_count = 0
        now = self._now()
        with self.connect() as connection:
            for item in unique.values():
                exists = connection.execute("SELECT 1 FROM jobs WHERE job_id=?", (item.job_id,)).fetchone()
                if exists:
                    connection.execute(
                        """UPDATE jobs SET
                           job_name=?, company=?, salary=?, salary_low=?, salary_high=?, experience=?, degree=?,
                           location=?, boss=?, skills=?, url=?, last_seen_at=?, last_seen_run_id=?, updated_at=?
                           WHERE job_id=?""",
                        (
                            item.job_name,
                            item.company,
                            item.salary,
                            item.salary_low,
                            item.salary_high,
                            item.experience,
                            item.degree,
                            item.location,
                            item.boss,
                            item.skills,
                            item.url,
                            item.fetched_at,
                            run_id,
                            now,
                            item.job_id,
                        ),
                    )
                else:
                    connection.execute(
                        """INSERT INTO jobs(
                           job_id, job_name, company, salary, salary_low, salary_high, experience, degree, location,
                           boss, skills, url, first_seen_at, last_seen_at, first_seen_run_id, last_seen_run_id,
                           created_at, updated_at
                           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            item.job_id,
                            item.job_name,
                            item.company,
                            item.salary,
                            item.salary_low,
                            item.salary_high,
                            item.experience,
                            item.degree,
                            item.location,
                            item.boss,
                            item.skills,
                            item.url,
                            item.fetched_at,
                            item.fetched_at,
                            run_id,
                            run_id,
                            now,
                            now,
                        ),
                    )
                    new_count += 1
        return new_count

    def get_job(self, job_id):
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        return dict(row) if row else None

    def count_jobs(self):
        with self.connect() as connection:
            return connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
