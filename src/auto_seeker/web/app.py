from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from auto_seeker.application.query_jobs import JobQuery, SortOrder
from auto_seeker.infrastructure.sqlite_repository import SQLiteJobRepository

WEB_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=WEB_DIR / "templates")


def create_app(database_path):
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
        page_size: int = Query(default=50),
    ):
        query = JobQuery(q, minimum_salary, maximum_experience, location, new_only, run_id, sort, page, page_size)
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

    return app
