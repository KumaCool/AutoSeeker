import unittest

from auto_seeker.application.query_jobs import JobQuery, QueryError, QueryPage, SortOrder


class JobQueryModelTests(unittest.TestCase):
    def test_normalizes_text_and_calculates_offset(self):
        query = JobQuery(q="  Vue  ", location=" 武汉 ", page=3, page_size=20)

        self.assertEqual(query.q, "Vue")
        self.assertEqual(query.location, "武汉")
        self.assertEqual(query.offset, 40)

    def test_default_query_is_stable(self):
        query = JobQuery()

        self.assertEqual(query.page, 1)
        self.assertEqual(query.page_size, 50)
        self.assertEqual(query.sort, SortOrder.NEWEST)
        self.assertFalse(query.new_only)
        self.assertIsNone(query.recruiter_status)

    def test_rejects_overlong_recruiter_status(self):
        with self.assertRaises(QueryError):
            JobQuery(recruiter_status="x" * 51)

    def test_rejects_invalid_pagination_salary_and_experience(self):
        invalid = [
            {"page": 0},
            {"page_size": 0},
            {"page_size": 21},
            {"minimum_salary": -1},
            {"maximum_experience": -1},
        ]
        for values in invalid:
            with self.subTest(values=values), self.assertRaises(QueryError):
                JobQuery(**values)

    def test_accepts_only_supported_page_sizes_and_sort_values(self):
        for size in (20, 50, 100):
            self.assertEqual(JobQuery(page_size=size).page_size, size)
        with self.assertRaises(QueryError):
            JobQuery(sort="company")

    def test_query_page_calculates_page_count(self):
        result = QueryPage(items=[{"job_id": "1"}], total=101, page=2, page_size=50)

        self.assertEqual(result.page_count, 3)
        self.assertTrue(result.has_previous)
        self.assertTrue(result.has_next)


if __name__ == "__main__":
    unittest.main()
