from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SearchCriteria:
    keyword: str
    city_code: str
    minimum_salary_k: float
    maximum_experience_years: int


@dataclass(frozen=True)
class Job:
    fetched_at: str
    job_name: str
    company: str
    salary: str
    salary_low: float
    salary_high: float
    experience: str
    degree: str
    location: str
    boss: str
    skills: str
    url: str
    job_id: str
    recruiter_status: str = "未知"

    def to_dict(self):
        return asdict(self)
