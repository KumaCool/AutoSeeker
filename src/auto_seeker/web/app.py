import secrets
import threading
from pathlib import Path
from urllib.parse import urlencode, urlparse

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from auto_seeker.application.collect_jobs import CollectionError
from auto_seeker.application.query_jobs import JobQuery, SortOrder
from auto_seeker.auth import AuthError, import_verified_cookies
from auto_seeker.infrastructure.sqlite_repository import SQLiteJobRepository

WEB_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=WEB_DIR / "templates")
MAX_COOKIE_FILE_SIZE = 1024 * 1024


def create_app(database_path, default_page_size=50, cookie_path=None, request_timeout=30, collect_runner=None):
    app = FastAPI(title="AutoSeeker", docs_url=None, redoc_url=None)
    repository = SQLiteJobRepository(database_path)
    app.state.repository = repository
    app.state.cookie_path = (
        Path(cookie_path) if cookie_path else Path(database_path).parent.parent / "secrets/cookies.json"
    )
    app.state.user_name = None
    app.state.csrf_token = secrets.token_urlsafe(32)
    app.state.collect_runner = collect_runner
    app.state.collect_stop = threading.Event()
    app.state.collect_state = {
        "running": False,
        "stopping": False,
        "run_id": None,
        "pages_completed": 0,
        "pages_requested": 0,
        "matched_count": 0,
        "new_count": 0,
        "message": None,
        "status": "idle",
    }
    app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")

    def shared_context():
        return {
            "user_name": app.state.user_name,
            "csrf_token": app.state.csrf_token,
        }

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
        minimum_salary: str | None = None,
        maximum_experience: str | None = None,
        location: str | None = None,
        recruiter_status: str | None = None,
        new_only: bool = False,
        run_id: str | None = None,
        sort: SortOrder = SortOrder.NEWEST,
        page: int = Query(default=1, ge=1),
        page_size: int | None = Query(default=None),
    ):
        effective_page_size = page_size if page_size is not None else default_page_size
        try:
            parsed_minimum_salary = float(minimum_salary) if minimum_salary not in (None, "") else None
            parsed_maximum_experience = int(maximum_experience) if maximum_experience not in (None, "") else None
            parsed_run_id = int(run_id) if run_id not in (None, "") else None
            query = JobQuery(
                q,
                parsed_minimum_salary,
                parsed_maximum_experience,
                location,
                recruiter_status,
                new_only,
                parsed_run_id,
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
            "recruiter_status": query.recruiter_status or "",
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
                **shared_context(),
                "query": query,
                "page": result,
                "cookie_imported": request.query_params.get("cookie_imported") == "1",
                "collect_status": request.query_params.get("collect_status"),
                "collect_notice": app.state.collect_state["message"],
                "collect_state": app.state.collect_state,
                "recruiter_statuses": repository.list_recruiter_statuses(),
                "previous_query": page_query(query.page - 1),
                "next_query": page_query(query.page + 1),
            },
        )

    @app.get("/jobs/{job_id}", include_in_schema=False)
    def job_detail(request: Request, job_id: str):
        job = repository.get_job_detail(job_id)
        if job is None:
            return templates.TemplateResponse(request, "errors/404.html", shared_context(), status_code=404)
        parsed = urlparse(job["url"])
        job["safe_url"] = (
            job["url"] if parsed.scheme == "https" and parsed.hostname in {"zhipin.com", "www.zhipin.com"} else None
        )
        return templates.TemplateResponse(request, "jobs/detail.html", {**shared_context(), "job": job})

    @app.get("/runs", include_in_schema=False)
    def collection_runs(request: Request):
        return templates.TemplateResponse(
            request,
            "runs/list.html",
            {
                **shared_context(),
                "runs": repository.list_runs(),
                "status_labels": {
                    "running": "进行中",
                    "completed": "已完成",
                    "partial": "部分完成",
                    "failed": "失败",
                },
            },
        )

    @app.post("/auth/cookies", include_in_schema=False)
    async def import_cookie_file(
        request: Request,
        csrf_token: str = Form(...),
        cookie_file: UploadFile = File(...),
    ):
        if not secrets.compare_digest(csrf_token, app.state.csrf_token):
            raise HTTPException(status_code=403, detail="CSRF 校验失败")
        if cookie_file.content_type != "application/json" or not (cookie_file.filename or "").lower().endswith(".json"):
            raise HTTPException(status_code=400, detail="只接受 JSON Cookie 文件")
        content = await cookie_file.read(MAX_COOKIE_FILE_SIZE + 1)
        if len(content) > MAX_COOKIE_FILE_SIZE:
            raise HTTPException(status_code=413, detail="Cookie 文件不得超过 1 MiB")
        try:
            app.state.user_name = import_verified_cookies(
                content,
                app.state.cookie_path,
                timeout=request_timeout,
            )
        except AuthError as exc:
            app.state.user_name = None
            return templates.TemplateResponse(
                request,
                "errors/cookie-import.html",
                {**shared_context(), "error": str(exc)},
                status_code=400,
            )
        return RedirectResponse("/jobs?cookie_imported=1", status_code=303)

    @app.post("/collect/start", include_in_schema=False)
    def start_collection(csrf_token: str = Form(...)):
        if not secrets.compare_digest(csrf_token, app.state.csrf_token):
            raise HTTPException(status_code=403, detail="CSRF 校验失败")
        if app.state.collect_state["running"]:
            raise HTTPException(status_code=409, detail="采集任务正在运行")
        app.state.collect_stop.clear()
        app.state.collect_state.update(
            running=True,
            stopping=False,
            run_id=None,
            pages_completed=0,
            pages_requested=0,
            matched_count=0,
            new_count=0,
            message=None,
            status="running",
        )

        def update_progress(**values):
            app.state.collect_state.update(values)

        def run_in_background():
            try:
                if app.state.collect_runner is None:
                    raise CollectionError("Web 采集器尚未配置")
                result = app.state.collect_runner(progress=update_progress, should_stop=app.state.collect_stop.is_set)
                stopped = app.state.collect_stop.is_set()
                app.state.collect_state.update(
                    running=False,
                    stopping=False,
                    status="stopped" if stopped else "success",
                    run_id=result.run_id,
                    pages_completed=result.pages_completed,
                    matched_count=result.matched_count,
                    new_count=result.new_count,
                    message=(
                        f"采集已停止：完成 {result.pages_completed} 页，匹配 {result.matched_count}。"
                        if stopped
                        else f"采集完成：批次 #{result.run_id}，匹配 {result.matched_count}，新增 {result.new_count}。"
                    ),
                )
            except CollectionError as exc:
                app.state.collect_state.update(
                    running=False,
                    stopping=False,
                    status="error",
                    message=repository._redact_error(exc),
                )

        threading.Thread(target=run_in_background, daemon=True).start()
        return RedirectResponse("/jobs?collect_status=running", status_code=303)

    @app.post("/collect/stop", include_in_schema=False)
    def stop_collection(csrf_token: str = Form(...)):
        if not secrets.compare_digest(csrf_token, app.state.csrf_token):
            raise HTTPException(status_code=403, detail="CSRF 校验失败")
        if not app.state.collect_state["running"]:
            raise HTTPException(status_code=409, detail="当前没有采集任务")
        app.state.collect_stop.set()
        app.state.collect_state["stopping"] = True
        app.state.collect_state["status"] = "stopping"
        return RedirectResponse("/jobs?collect_status=stopping", status_code=303)

    @app.get("/collect/status", include_in_schema=False)
    def collection_status():
        return dict(app.state.collect_state)

    return app
