import re
from datetime import datetime

from boss_zhipin.domain.salary import parse_salary
from boss_zhipin.models import Job


def experience_max_years(text):
    text = str(text or "")
    if any(word in text for word in ("经验不限", "不限", "应届", "在校")):
        return 0
    numbers = [int(value) for value in re.findall(r"\d+", text)]
    if not numbers:
        return None
    if "以内" in text:
        return numbers[0]
    return max(numbers)


def extract_jobs(payload, criteria, fetched_at=None):
    raw_jobs = (payload.get("zpData") or {}).get("jobList") or (payload.get("zpData") or {}).get("list") or []
    fetched_at = fetched_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    jobs = []
    for item in raw_jobs:
        salary = item.get("salaryDesc") or item.get("salary") or ""
        experience = item.get("jobExperience") or item.get("experienceName") or ""
        salary_low, salary_high = parse_salary(salary)
        max_years = experience_max_years(experience)
        if salary_low is None or salary_low < criteria.minimum_salary_k:
            continue
        if max_years is None or max_years > criteria.maximum_experience_years:
            continue
        encrypt_job_id = str(item.get("encryptJobId") or "")
        job_id = encrypt_job_id or str(item.get("jobId") or "")
        url = item.get("jobUrl") or item.get("url") or ""
        if url.startswith("/"):
            url = "https://www.zhipin.com" + url
        if not url and encrypt_job_id:
            url = f"https://www.zhipin.com/job_detail/{encrypt_job_id}.html"
        location = " ".join(filter(None, [item.get("cityName"), item.get("areaDistrict"), item.get("businessDistrict")]))
        skills = item.get("skills") or item.get("jobLabels") or []
        if isinstance(skills, list):
            skills = "、".join(map(str, skills))
        jobs.append(Job(
            fetched_at=fetched_at, job_name=item.get("jobName") or item.get("positionName") or "",
            company=item.get("brandName") or item.get("companyName") or "", salary=salary,
            salary_low=salary_low, salary_high=salary_high, experience=experience,
            degree=item.get("jobDegree") or item.get("degreeName") or "", location=location,
            boss=item.get("bossName") or "", skills=str(skills), url=url, job_id=job_id or url,
        ))
    return jobs
