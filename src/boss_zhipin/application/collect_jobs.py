import time
from dataclasses import dataclass

from boss_zhipin.domain.filtering import extract_jobs


class CollectionError(RuntimeError):
    pass


@dataclass(frozen=True)
class CollectionResult:
    pages_completed: int
    matched_count: int
    new_count: int


def collect_jobs(client, stoken, repository, criteria, start_page, page_count, interval: float = 0, sleep=time.sleep):
    collected = {}
    failure = None
    pages_completed = 0
    for page in range(start_page, start_page + page_count):
        try:
            payload = client.request_page(page)
            if payload.get("code") == 37:
                stoken.refresh(payload)
                payload = client.request_page(page)
                if payload.get("code") == 37:
                    raise CollectionError("安全刷新后仍返回 code=37")
            jobs = extract_jobs(payload, criteria)
            for job in jobs:
                collected[job.job_id] = job
            pages_completed += 1
            sleep(interval)
        except Exception as exc:
            failure = exc
            break
    new_count = repository.save(list(collected.values())) if collected else 0
    result = CollectionResult(pages_completed, len(collected), new_count)
    if failure:
        raise CollectionError(f"任务未完成，已保存部分结果：{failure}") from failure
    return result
