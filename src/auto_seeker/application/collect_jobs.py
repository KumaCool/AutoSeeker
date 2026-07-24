import time
from dataclasses import dataclass, replace

from auto_seeker.domain.filtering import extract_jobs


class CollectionError(RuntimeError):
    def __init__(self, message, result=None):
        super().__init__(message)
        self.result = result


class CollectionStopped(RuntimeError):
    pass


@dataclass(frozen=True)
class CollectionResult:
    run_id: int
    pages_completed: int
    matched_count: int
    new_count: int


def _recruiter_status(payload):
    boss = (payload.get("zpData") or {}).get("bossInfo") or {}
    if boss.get("bossOnline") is True:
        return "在线"
    description = boss.get("activeTimeDesc")
    return description.strip() if isinstance(description, str) and description.strip() else "未知"


def _enrich_recruiter_status(client, stoken, job):
    if not job.security_id:
        return replace(job, recruiter_status="在线" if job.recruiter_status == "在线" else "未知")
    payload = client.request_job_detail(job)
    if payload.get("code") == 37:
        stoken.refresh(payload)
        payload = client.request_job_detail(job)
        if payload.get("code") == 37:
            return replace(job, recruiter_status="未知")
    return replace(job, recruiter_status=_recruiter_status(payload))


def collect_jobs(
    client,
    stoken,
    repository,
    criteria,
    start_page,
    page_count,
    interval: float = 0,
    sleep=time.sleep,
    progress=None,
    should_stop=None,
):
    run_id = repository.begin_run(pages_requested=page_count)
    collected = {}
    failure = None
    pages_completed = 0
    if progress:
        progress(run_id=run_id, pages_completed=0, pages_requested=page_count, matched_count=0)
    for page in range(start_page, start_page + page_count):
        if should_stop and should_stop():
            failure = CollectionStopped("用户停止采集")
            break
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
            if progress:
                progress(
                    run_id=run_id,
                    pages_completed=pages_completed,
                    pages_requested=page_count,
                    matched_count=len(collected),
                )
            sleep(interval)
        except Exception as exc:
            failure = exc
            break
    try:
        jobs_to_enrich = list(collected.values())
        if isinstance(failure, CollectionStopped):
            enriched = jobs_to_enrich
        else:
            enriched = []
            for index, job in enumerate(jobs_to_enrich):
                if should_stop and should_stop():
                    enriched.extend(jobs_to_enrich[index:])
                    failure = CollectionStopped("用户停止采集")
                    break
                try:
                    enriched.append(_enrich_recruiter_status(client, stoken, job))
                except Exception:
                    enriched.append(replace(job, recruiter_status="未知"))
                sleep(interval)
        new_count = repository.save_jobs(run_id, enriched) if enriched else 0
    except Exception as storage_error:
        result = CollectionResult(run_id, pages_completed, len(collected), 0)
        repository.fail_run(
            run_id,
            pages_completed=pages_completed,
            matched_count=len(collected),
            error=storage_error,
            partial=False,
        )
        raise CollectionError(f"本地存储失败：{storage_error}", result) from storage_error
    result = CollectionResult(run_id, pages_completed, len(collected), new_count)
    if failure:
        repository.fail_run(
            run_id,
            pages_completed=pages_completed,
            matched_count=len(collected),
            error=failure,
            partial=bool(collected),
        )
        if isinstance(failure, CollectionStopped):
            return result
        raise CollectionError(f"任务未完成，已保存部分结果：{failure}", result) from failure
    repository.complete_run(
        run_id,
        pages_completed=pages_completed,
        matched_count=len(collected),
        new_count=new_count,
    )
    return result
