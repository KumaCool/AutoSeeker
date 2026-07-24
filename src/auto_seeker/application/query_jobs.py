from dataclasses import dataclass
from enum import StrEnum
from math import ceil
from typing import Any


class QueryError(ValueError):
    pass


class SortOrder(StrEnum):
    NEWEST = "newest"
    SALARY_DESC = "salary_desc"
    LAST_SEEN = "last_seen"


@dataclass(frozen=True)
class JobQuery:
    q: str | None = None
    minimum_salary: float | None = None
    maximum_experience: int | None = None
    location: str | None = None
    recruiter_status: str | None = None
    new_only: bool = False
    run_id: int | None = None
    sort: SortOrder = SortOrder.NEWEST
    page: int = 1
    page_size: int = 50

    def __post_init__(self):
        q = self.q.strip() if self.q else None
        location = self.location.strip() if self.location else None
        recruiter_status = self.recruiter_status.strip() if self.recruiter_status else None
        if recruiter_status not in {None, "在线", "离线", "未知"}:
            raise QueryError(f"不支持的招聘者状态：{recruiter_status}")
        try:
            sort = self.sort if isinstance(self.sort, SortOrder) else SortOrder(self.sort)  # type: ignore[arg-type]
        except ValueError as exc:
            raise QueryError(f"不支持的排序：{self.sort}") from exc
        if self.page < 1:
            raise QueryError("page 必须大于等于 1")
        if self.page_size not in {20, 50, 100}:
            raise QueryError("page_size 只允许 20、50 或 100")
        if self.minimum_salary is not None and self.minimum_salary < 0:
            raise QueryError("minimum_salary 不得为负")
        if self.maximum_experience is not None and self.maximum_experience < 0:
            raise QueryError("maximum_experience 不得为负")
        if self.run_id is not None and self.run_id < 1:
            raise QueryError("run_id 必须大于等于 1")
        object.__setattr__(self, "q", q or None)
        object.__setattr__(self, "location", location or None)
        object.__setattr__(self, "recruiter_status", recruiter_status)
        object.__setattr__(self, "sort", sort)

    @property
    def offset(self):
        return (self.page - 1) * self.page_size


@dataclass(frozen=True)
class QueryPage:
    items: list[dict[str, Any]]
    total: int
    page: int
    page_size: int

    @property
    def page_count(self):
        return ceil(self.total / self.page_size) if self.total else 0

    @property
    def has_previous(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.page_count
