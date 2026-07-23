import os
import tomllib
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(os.environ.get("AUTOSEEKER_PROJECT_ROOT", Path.cwd())).resolve()


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class SearchConfig:
    keyword: str
    city_code: str
    start_page: int
    page_count: int
    page_size: int
    minimum_salary_k: float
    maximum_experience_years: int


@dataclass(frozen=True)
class RequestConfig:
    interval_seconds: float
    timeout_seconds: int
    max_security_refreshes: int


@dataclass(frozen=True)
class StorageConfig:
    database: Path


@dataclass(frozen=True)
class WebConfig:
    host: str
    port: int
    page_size: int


@dataclass(frozen=True)
class RuntimeConfig:
    cache_dir: Path
    log_dir: Path
    cookie_file: Path


@dataclass(frozen=True)
class AppConfig:
    search: SearchConfig
    request: RequestConfig
    storage: StorageConfig
    web: WebConfig
    runtime: RuntimeConfig


ENV_KEYS = {
    "AUTOSEEKER_KEYWORD": "search.keyword",
    "AUTOSEEKER_CITY_CODE": "search.city_code",
    "AUTOSEEKER_START_PAGE": "search.start_page",
    "AUTOSEEKER_PAGE_COUNT": "search.page_count",
    "AUTOSEEKER_PAGE_SIZE": "search.page_size",
    "AUTOSEEKER_MINIMUM_SALARY_K": "search.minimum_salary_k",
    "AUTOSEEKER_MAXIMUM_EXPERIENCE_YEARS": "search.maximum_experience_years",
    "AUTOSEEKER_REQUEST_INTERVAL_SECONDS": "request.interval_seconds",
    "AUTOSEEKER_REQUEST_TIMEOUT_SECONDS": "request.timeout_seconds",
    "AUTOSEEKER_COOKIE_FILE": "runtime.cookie_file",
    "AUTOSEEKER_DATABASE": "storage.database",
    "AUTOSEEKER_WEB_HOST": "web.host",
    "AUTOSEEKER_WEB_PORT": "web.port",
    "AUTOSEEKER_WEB_PAGE_SIZE": "web.page_size",
}


def _merge(base: dict[str, Any], update: dict[str, Any]):
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value


def _set(data: dict[str, Any], dotted_key: str, value: Any):
    section, key = dotted_key.split(".", 1)
    data.setdefault(section, {})[key] = value


def _coerce(value: str, current: Any):
    if isinstance(current, bool):
        return value.lower() in {"1", "true", "yes"}
    if isinstance(current, int):
        return int(value)
    if isinstance(current, float):
        return float(value)
    return value


def _positive(name: str, value: int | float):
    if value <= 0:
        raise ConfigError(f"{name} 必须大于 0")
    return value


def load_config(path: str | Path | None = None, overrides: dict[str, Any] | None = None):
    with files("auto_seeker").joinpath("default.toml").open("rb") as stream:
        data = tomllib.load(stream)
    if path is not None:
        with Path(path).open("rb") as stream:
            _merge(data, tomllib.load(stream))
    for env_name, dotted_key in ENV_KEYS.items():
        if env_name in os.environ:
            section, key = dotted_key.split(".", 1)
            _set(data, dotted_key, _coerce(os.environ[env_name], data[section][key]))
    for key, value in (overrides or {}).items():
        if value is not None:
            _set(data, key, value)

    search = data["search"]
    request = data["request"]
    web = data["web"]
    web_port = int(web["port"])
    if not 1 <= web_port <= 65535:
        raise ConfigError("web.port 必须位于 1..65535")
    web_page_size = int(web["page_size"])
    if web_page_size not in {20, 50, 100}:
        raise ConfigError("web.page_size 只允许 20、50 或 100")
    return AppConfig(
        search=SearchConfig(
            keyword=str(search["keyword"]),
            city_code=str(search["city_code"]),
            start_page=int(_positive("start_page", int(search["start_page"]))),
            page_count=int(_positive("page_count", int(search["page_count"]))),
            page_size=int(_positive("page_size", int(search["page_size"]))),
            minimum_salary_k=float(_positive("minimum_salary_k", float(search["minimum_salary_k"]))),
            maximum_experience_years=int(search["maximum_experience_years"]),
        ),
        request=RequestConfig(
            interval_seconds=float(_positive("interval_seconds", float(request["interval_seconds"]))),
            timeout_seconds=int(_positive("timeout_seconds", int(request["timeout_seconds"]))),
            max_security_refreshes=int(_positive("max_security_refreshes", int(request["max_security_refreshes"]))),
        ),
        storage=StorageConfig(database=Path(data["storage"]["database"])),
        web=WebConfig(host=str(web["host"]), port=web_port, page_size=web_page_size),
        runtime=RuntimeConfig(
            cache_dir=Path(data["runtime"]["cache_dir"]),
            log_dir=Path(data["runtime"]["log_dir"]),
            cookie_file=Path(data["runtime"]["cookie_file"]),
        ),
    )
