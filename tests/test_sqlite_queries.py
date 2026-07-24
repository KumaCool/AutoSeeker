import tempfile
import unittest
from pathlib import Path

from auto_seeker.application.query_jobs import JobQuery, SortOrder
from auto_seeker.infrastructure.sqlite_repository import SQLiteJobRepository
from auto_seeker.models import Job


def job(job_id, name, company, salary_low, experience, location, skills, fetched_at):
    return Job(
        fetched_at=fetched_at,
        job_name=name,
        company=company,
        salary=f"{salary_low}-{salary_low + 5}K",
        salary_low=salary_low,
        salary_high=salary_low + 5,
        experience=experience,
        degree="本科",
        location=location,
        boss="招聘者",
        skills=skills,
        url=f"https://www.zhipin.com/job_detail/{job_id}.html",
        job_id=job_id,
    )


class SQLiteQueryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.repository = SQLiteJobRepository(Path(self.directory.name) / "autoseeker.sqlite3")
        first = self.repository.begin_run(pages_requested=1)
        self.repository.save_jobs(
            first,
            [
                job("1", "Vue 前端", "甲公司", 20, "1-3年", "武汉·光谷", "Vue TypeScript", "2026-07-24 08:00:00"),
                job("2", "Python 后端", "乙公司", 30, "3-5年", "上海", "Python FastAPI", "2026-07-24 09:00:00"),
                job("3", "React 前端", "丙公司", 18, "经验不限", "武汉·江夏", "React", "2026-07-24 10:00:00"),
            ],
        )
        self.repository.complete_run(first, pages_completed=1, matched_count=3, new_count=3)
        second = self.repository.begin_run(pages_requested=1)
        self.repository.save_jobs(
            second,
            [job("1", "Vue 前端", "甲公司", 22, "1-3年", "武汉·光谷", "Vue TypeScript", "2026-07-25 08:00:00")],
        )
        self.repository.complete_run(second, pages_completed=1, matched_count=1, new_count=0)
        self.first_run = first
        self.second_run = second

    def tearDown(self):
        self.directory.cleanup()

    def test_empty_repository_returns_empty_page(self):
        empty = SQLiteJobRepository(Path(self.directory.name) / "empty.sqlite3")

        page = empty.query_jobs(JobQuery())

        self.assertEqual(page.items, [])
        self.assertEqual(page.total, 0)
        self.assertEqual(page.page_count, 0)

    def test_combined_text_salary_experience_and_location_filters(self):
        page = self.repository.query_jobs(
            JobQuery(q="vue", minimum_salary=20, maximum_experience=3, location="武汉", sort=SortOrder.SALARY_DESC)
        )

        self.assertEqual(page.total, 1)
        self.assertEqual(page.items[0]["job_id"], "1")
        self.assertTrue(page.items[0]["is_new"] is False)

    def test_text_search_matches_company_and_skills_case_insensitively(self):
        company = self.repository.query_jobs(JobQuery(q="乙公司"))
        skills = self.repository.query_jobs(JobQuery(q="react"))

        self.assertEqual([item["job_id"] for item in company.items], ["2"])
        self.assertEqual([item["job_id"] for item in skills.items], ["3"])

    def test_filters_by_recruiter_status(self):
        with self.repository.connect() as connection:
            connection.execute("UPDATE jobs SET recruiter_status='在线' WHERE job_id='1'")
            connection.execute("UPDATE jobs SET recruiter_status='离线' WHERE job_id='2'")

        page = self.repository.query_jobs(JobQuery(recruiter_status="在线"))

        self.assertEqual([item["job_id"] for item in page.items], ["1"])

    def test_new_only_uses_latest_completed_run(self):
        page = self.repository.query_jobs(JobQuery(new_only=True))

        self.assertEqual(page.total, 0)
        self.assertEqual(page.items, [])

    def test_run_filter_matches_last_seen_run(self):
        page = self.repository.query_jobs(JobQuery(run_id=self.first_run))

        self.assertEqual({item["job_id"] for item in page.items}, {"2", "3"})

    def test_default_sort_is_new_first_then_last_seen_then_salary(self):
        third = self.repository.begin_run(pages_requested=1)
        self.repository.save_jobs(
            third,
            [job("4", "新职位", "丁公司", 16, "经验不限", "武汉", "HTML", "2026-07-26 08:00:00")],
        )
        self.repository.complete_run(third, pages_completed=1, matched_count=1, new_count=1)

        page = self.repository.query_jobs(JobQuery())

        self.assertEqual([item["job_id"] for item in page.items], ["4", "1", "3", "2"])
        self.assertTrue(page.items[0]["is_new"])

    def test_pagination_and_page_out_of_range(self):
        first_page = self.repository.query_jobs(JobQuery(page=1, page_size=20))
        beyond = self.repository.query_jobs(JobQuery(page=2, page_size=20))

        self.assertEqual(first_page.total, 3)
        self.assertEqual(len(first_page.items), 3)
        self.assertEqual(beyond.total, 3)
        self.assertEqual(beyond.items, [])

    def test_list_runs_and_get_job_are_read_only_views(self):
        runs = self.repository.list_runs(limit=1)
        saved = self.repository.get_job_detail("1")

        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["id"], self.second_run)
        self.assertEqual(saved["job_id"], "1")
        self.assertEqual(saved["first_seen_run_id"], self.first_run)


if __name__ == "__main__":
    unittest.main()
