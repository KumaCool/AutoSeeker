from pathlib import Path
from urllib.parse import urlencode, urlparse

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from auto_seeker.application.query_jobs import JobQuery, SortOrder
from auto_seeker.infrastructure.sqlite_repository import SQLiteJobRepository

WEB_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=WEB_DIR / "templates")


def create_app(database_path, default_page_size=50):
    app = FastAPI(title="AutoSeeker", docs_url=None, redoc_url=None)
    repository = SQLiteJobRepository(database_path)
    app.state.repository = repository
    app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse("/jobs")

    @app.get("/health")
    def health():
        with repository.connect() as connection:
            connection.execute("SELECT 1").fetchone()
        return {"status": "ok", "database": "ok"}

    @app.get("/jobs", include_in_schema=False)
    def jobs(
        request: Request,
        q: str | None = None,
        minimum_salary: float | None = Query(default=None, ge=0),
        maximum_experience: int | None = Query(default=None, ge=0),
        location: str | None = None,
        new_only: bool = False,
        run_id: int | None = Query(default=None, ge=1),
        sort: SortOrder = SortOrder.NEWEST,
        page: int = Query(default=1, ge=1),
        page_size: int | None = Query(default=None),
    ):
        effective_page_size = page_size if page_size is not None else default_page_size
        try:
            query = JobQuery(
                q,
                minimum_salary,
                maximum_experience,
                location,
                new_only,
                run_id,
                sort,
                page,
                effective_page_size,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        result = repository.query_jobs(query)
        values = {
            "q": query.q or "",
            "minimum_salary": query.minimum_salary,
            "maximum_experience": query.maximum_experience,
            "location": query.location or "",
            "new_only": "1" if query.new_only else "",
            "run_id": query.run_id,
            "sort": query.sort.value,
            "page_size": query.page_size,
        }

        def page_query(number):
            return urlencode(
                {**{key: value for key, value in values.items() if value not in (None, "")}, "page": number}
            )

        return templates.TemplateResponse(
            request,
            "jobs/list.html",
            {
                "query": query,
                "page": result,
                "previous_query": page_query(query.page - 1),
                "next_query": page_query(query.page + 1),
            },
        )

    @app.get("/jobs/{job_id}", include_in_schema=False)
    def job_detail(request: Request, job_id: str):
        job = repository.get_job_detail(job_id)
        if job is None:
            return templates.TemplateResponse(request, "errors/404.html", status_code=404)
        parsed = urlparse(job["url"])
        job["safe_url"] = (
            job["url"] if parsed.scheme == "https" and parsed.hostname in {"zhipin.com", "www.zhipin.com"} else None
        )
        return templates.TemplateResponse(request, "jobs/detail.html", {"job": job})

    @app.get("/runs", include_in_schema=False)
    def collection_runs(request: Request):
        return templates.TemplateResponse(
            request,
            "runs/list.html",
            {
                "runs": repository.list_runs(),
                "status_labels": {
                    "running": "进行中",
                    "completed": "已完成",
                    "partial": "部分完成",
                    "failed": "失败",
                },
            },
        )

    return app
