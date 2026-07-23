import unittest

from boss_zhipin.domain.filtering import extract_jobs, experience_max_years
from boss_zhipin.domain.salary import parse_salary
from boss_zhipin.models import SearchCriteria


class DomainTests(unittest.TestCase):
    def test_salary_and_experience_parsing(self):
        self.assertEqual(parse_salary("15-25K·14薪"), (15.0, 25.0))
        self.assertEqual(experience_max_years("1-3年"), 3)
        self.assertEqual(experience_max_years("经验不限"), 0)

    def test_extract_jobs_returns_typed_filtered_job(self):
        criteria = SearchCriteria(keyword="前端", city_code="101200100", minimum_salary_k=15, maximum_experience_years=3)
        payload = {"zpData": {"jobList": [{
            "salaryDesc": "15-25K", "jobExperience": "1-3年",
            "encryptJobId": "job-id", "jobName": "前端开发", "brandName": "示例公司",
            "cityName": "武汉", "skills": ["Vue", "TypeScript"],
        }]}}

        jobs = extract_jobs(payload, criteria, fetched_at="2026-07-23 00:00:00")

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].job_id, "job-id")
        self.assertEqual(jobs[0].skills, "Vue、TypeScript")
        self.assertEqual(jobs[0].url, "https://www.zhipin.com/job_detail/job-id.html")


if __name__ == "__main__":
    unittest.main()
