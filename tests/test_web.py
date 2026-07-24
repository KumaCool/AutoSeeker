import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

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
            ),
            Job(
                fetched_at="2026-07-24 09:00:00",
                job_name="不安全链接",
                company="示例公司",
                salary="20-30K",
                salary_low=20,
                salary_high=30,
                experience="经验不限",
                degree="本科",
                location="武汉",
                boss="招聘者",
                skills="HTML",
                url="javascript:alert(1)",
                job_id="unsafe",
            ),
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


class CookieImportWebTests(unittest.TestCase):
    def test_navigation_shows_import_button_when_logged_out(self):
        with tempfile.TemporaryDirectory() as directory:
            response = TestClient(create_app(Path(directory) / "autoseeker.sqlite3")).get("/jobs")

        self.assertIn("导入登录 Cookie", response.text)

    def test_verified_upload_redirects_and_navigation_shows_user_name(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = create_app(root / "autoseeker.sqlite3", cookie_path=root / "cookies.json")
            client = TestClient(app)
            with patch("auto_seeker.web.app.import_verified_cookies", return_value="Kuma") as importer:
                response = client.post(
                    "/auth/cookies",
                    data={"csrf_token": app.state.csrf_token},
                    files={"cookie_file": ("cookies.json", b"[]", "application/json")},
                    follow_redirects=False,
                )

            self.assertEqual(response.status_code, 303)
            self.assertEqual(response.headers["location"], "/jobs?cookie_imported=1")
            importer.assert_called_once()
            self.assertIn("Kuma", client.get("/jobs").text)

    def test_upload_rejects_wrong_csrf_without_importing(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(Path(directory) / "autoseeker.sqlite3")
            with patch("auto_seeker.web.app.import_verified_cookies") as importer:
                response = TestClient(app).post(
                    "/auth/cookies",
                    data={"csrf_token": "wrong"},
                    files={"cookie_file": ("cookies.json", b"[]", "application/json")},
                )

        self.assertEqual(response.status_code, 403)
        importer.assert_not_called()

    def test_upload_rejects_non_json_and_oversized_files(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(Path(directory) / "autoseeker.sqlite3")
            client = TestClient(app)
            wrong_type = client.post(
                "/auth/cookies",
                data={"csrf_token": app.state.csrf_token},
                files={"cookie_file": ("cookies.txt", b"x", "text/plain")},
            )
            too_large = client.post(
                "/auth/cookies",
                data={"csrf_token": app.state.csrf_token},
                files={"cookie_file": ("cookies.json", b"x" * (1024 * 1024 + 1), "application/json")},
            )

        self.assertEqual(wrong_type.status_code, 400)
        self.assertEqual(too_large.status_code, 413)

    def test_failed_verification_renders_error_and_keeps_user_logged_out(self):
        from auto_seeker.auth import AuthError

        with tempfile.TemporaryDirectory() as directory:
            app = create_app(Path(directory) / "autoseeker.sqlite3")
            client = TestClient(app)
            with patch("auto_seeker.web.app.import_verified_cookies", side_effect=AuthError("业务码=36")):
                response = client.post(
                    "/auth/cookies",
                    data={"csrf_token": app.state.csrf_token},
                    files={"cookie_file": ("cookies.json", b"[]", "application/json")},
                )

        self.assertEqual(response.status_code, 400)
        self.assertIn("业务码=36", response.text)
        self.assertIsNone(app.state.user_name)


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
        self.assertIn("招聘者状态", response.text)
        self.assertIn("未知", response.text)

    def test_invalid_query_returns_422_without_database_error(self):
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(Path(directory) / "autoseeker.sqlite3"))
            response = client.get("/jobs?page=0")

        self.assertEqual(response.status_code, 422)

    def test_empty_numeric_form_fields_are_treated_as_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            response = TestClient(create_app(Path(directory) / "autoseeker.sqlite3")).get(
                "/jobs?minimum_salary=&maximum_experience=&run_id="
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("尚无采集数据", response.text)

    def test_invalid_page_size_returns_422(self):
        with tempfile.TemporaryDirectory() as directory:
            response = TestClient(create_app(Path(directory) / "autoseeker.sqlite3")).get("/jobs?page_size=21")

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

    def test_untrusted_job_url_is_not_rendered_as_link(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(Path(directory) / "autoseeker.sqlite3")
            seed_jobs(app)
            response = TestClient(app).get("/jobs/unsafe")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("javascript:alert(1)", response.text)
        self.assertNotIn("前往 BOSS 查看详情", response.text)


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


class WebCollectionTests(unittest.TestCase):
    def test_jobs_heading_has_collect_button(self):
        with tempfile.TemporaryDirectory() as directory:
            response = TestClient(create_app(Path(directory) / "autoseeker.sqlite3")).get("/jobs")

        self.assertIn(">采集</button>", response.text)
        self.assertIn('action="/collect/start"', response.text)

    def test_start_requires_valid_csrf(self):
        runner = Mock()
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(Path(directory) / "autoseeker.sqlite3", collect_runner=runner)
            response = TestClient(app).post("/collect/start", data={"csrf_token": "wrong"})

        self.assertEqual(response.status_code, 403)
        runner.assert_not_called()

    def test_start_runs_in_background_and_status_reports_progress(self):
        started = threading.Event()
        release = threading.Event()

        def runner(progress=None, should_stop=None):
            progress(run_id=7, pages_completed=1, pages_requested=5, matched_count=12)
            started.set()
            release.wait(timeout=2)
            return Mock(run_id=7, pages_completed=1, matched_count=12, new_count=3)

        with tempfile.TemporaryDirectory() as directory:
            app = create_app(Path(directory) / "autoseeker.sqlite3", collect_runner=runner)
            client = TestClient(app)
            response = client.post("/collect/start", data={"csrf_token": app.state.csrf_token}, follow_redirects=False)
            started.wait(timeout=1)
            running = client.get("/collect/status").json()
            release.set()
            for _ in range(50):
                finished = client.get("/collect/status").json()
                if not finished["running"]:
                    break
                threading.Event().wait(0.01)

        self.assertEqual(response.status_code, 303)
        self.assertTrue(running["running"])
        self.assertEqual(running["pages_completed"], 1)
        self.assertEqual(running["pages_requested"], 5)
        self.assertEqual(running["matched_count"], 12)
        self.assertFalse(finished["running"])
        self.assertEqual(finished["new_count"], 3)

    def test_running_page_shows_stop_button(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(Path(directory) / "autoseeker.sqlite3", collect_runner=Mock())
            app.state.collect_state["running"] = True
            response = TestClient(app).get("/jobs")

        self.assertIn(">停止</button>", response.text)
        self.assertIn('action="/collect/stop"', response.text)

    def test_stop_sets_cooperative_stop_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(Path(directory) / "autoseeker.sqlite3", collect_runner=Mock())
            app.state.collect_state["running"] = True
            response = TestClient(app).post(
                "/collect/stop", data={"csrf_token": app.state.csrf_token}, follow_redirects=False
            )

        self.assertEqual(response.status_code, 303)
        self.assertTrue(app.state.collect_stop.is_set())
        self.assertTrue(app.state.collect_state["stopping"])

    def test_second_start_returns_conflict(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(Path(directory) / "autoseeker.sqlite3", collect_runner=Mock())
            app.state.collect_state["running"] = True
            response = TestClient(app).post("/collect/start", data={"csrf_token": app.state.csrf_token})

        self.assertEqual(response.status_code, 409)


if __name__ == "__main__":
    unittest.main()
