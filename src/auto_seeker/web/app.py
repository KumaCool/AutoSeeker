from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from auto_seeker.infrastructure.sqlite_repository import SQLiteJobRepository

WEB_DIR = Path(__file__).resolve().parent


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
    def jobs_placeholder():
        return {"items": []}

    return app
