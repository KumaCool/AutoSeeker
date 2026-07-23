import sqlite3
from contextlib import contextmanager
from pathlib import Path

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
