import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from auto_seeker.models import Job
from auto_seeker.web.app import create_app


def seed_jobs(app):
    repository = app.state.repository
    first = repository.begin_run(pages_requested=1)
    repository.save_jobs(
        first,
        [
            Job(
                fetched_at="2026-07-24 08:00:00",
                job_name="<script>alert(1)</script>Vue 前端",
                company="示例公司",
                salary="20-30K",
                salary_low=20,
                salary_high=30,
                experience="1-3年",
                degree="本科",
                location="武汉·光谷",
                boss="招聘者",
                skills="Vue TypeScript",
                url="https://www.zhipin.com/job_detail/id-1.html",
                job_id="id-1",
            )
        ],
    )
    repository.complete_run(first, pages_completed=1, matched_count=1, new_count=1)


class WebHealthTests(unittest.TestCase):
    def test_root_redirects_to_jobs(self):
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(Path(directory) / "autoseeker.sqlite3"))
            response = client.get("/", follow_redirects=False)

        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers["location"], "/jobs")

    def test_health_checks_database_without_network(self):
        with tempfile.TemporaryDirectory() as directory, patch("requests.Session.request") as network:
            client = TestClient(create_app(Path(directory) / "autoseeker.sqlite3"))
            response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "ok"})
        network.assert_not_called()

    def test_static_css_is_served(self):
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(Path(directory) / "autoseeker.sqlite3"))
            response = client.get("/static/app.css")

        self.assertEqual(response.status_code, 200)
        self.assertIn("--accent", response.text)


class JobListWebTests(unittest.TestCase):
    def test_empty_database_shows_friendly_state(self):
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(Path(directory) / "autoseeker.sqlite3"))
            response = client.get("/jobs")

        self.assertEqual(response.status_code, 200)
        self.assertIn("尚无采集数据", response.text)
        self.assertIn("AutoSeeker", response.text)
        self.assertNotIn("第 1 页 / 共 0 页", response.text)

    def test_list_renders_filters_and_escapes_content(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(Path(directory) / "autoseeker.sqlite3")
            seed_jobs(app)
            client = TestClient(app)
            response = client.get("/jobs?q=Vue&minimum_salary=15&maximum_experience=3&location=武汉&new_only=1")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Vue 前端", response.text)
        self.assertNotIn("<script>alert(1)</script>", response.text)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", response.text)
        self.assertIn('value="Vue"', response.text)
        self.assertIn('value="武汉"', response.text)
        self.assertIn("1 个职位", response.text)

    def test_invalid_query_returns_422_without_database_error(self):
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(Path(directory) / "autoseeker.sqlite3"))
            response = client.get("/jobs?page=0")

        self.assertEqual(response.status_code, 422)


class JobDetailWebTests(unittest.TestCase):
    def test_detail_renders_fields_and_safe_external_link(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(Path(directory) / "autoseeker.sqlite3")
            seed_jobs(app)
            response = TestClient(app).get("/jobs/id-1")

        self.assertEqual(response.status_code, 200)
        self.assertIn("示例公司", response.text)
        self.assertIn("首次发现", response.text)
        self.assertIn('target="_blank"', response.text)
        self.assertIn('rel="noopener noreferrer"', response.text)
        self.assertNotIn("<script>alert(1)</script>", response.text)

    def test_missing_job_returns_html_404(self):
        with tempfile.TemporaryDirectory() as directory:
            response = TestClient(create_app(Path(directory) / "autoseeker.sqlite3")).get("/jobs/missing")

        self.assertEqual(response.status_code, 404)
        self.assertIn("没有找到这个职位", response.text)
        self.assertIn("text/html", response.headers["content-type"])


class CollectionRunsWebTests(unittest.TestCase):
    def test_runs_show_status_counts_and_safe_error_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(Path(directory) / "autoseeker.sqlite3")
            repository = app.state.repository
            completed = repository.begin_run(pages_requested=5)
            repository.complete_run(completed, pages_completed=5, matched_count=12, new_count=3)
            failed = repository.begin_run(pages_requested=1)
            repository.fail_run(
                failed,
                pages_completed=0,
                matched_count=0,
                error=RuntimeError("zp_at=secret-value <script>alert(1)</script>"),
                partial=False,
            )
            response = TestClient(app).get("/runs")

        self.assertEqual(response.status_code, 200)
        self.assertIn("采集记录", response.text)
        self.assertIn("已完成", response.text)
        self.assertIn("失败", response.text)
        self.assertIn("12", response.text)
        self.assertNotIn("secret-value", response.text)
        self.assertNotIn("<script>alert(1)</script>", response.text)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", response.text)

    def test_empty_runs_page_has_empty_state(self):
        with tempfile.TemporaryDirectory() as directory:
            response = TestClient(create_app(Path(directory) / "autoseeker.sqlite3")).get("/runs")

        self.assertEqual(response.status_code, 200)
        self.assertIn("还没有采集记录", response.text)


if __name__ == "__main__":
    unittest.main()
