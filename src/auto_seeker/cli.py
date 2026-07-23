import argparse
import json
from collections.abc import Sequence

from auto_seeker import __version__


def build_parser():
    parser = argparse.ArgumentParser(prog="autoseeker", description="AutoSeeker 自动职位发现与筛选工具")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--config", help="TOML 配置文件路径")
    subparsers = parser.add_subparsers(dest="command", required=True)
    collect = subparsers.add_parser("collect", help="采集职位并写入 SQLite")
    collect.add_argument("--keyword")
    collect.add_argument("--city-code")
    collect.add_argument("--page-count", type=int)
    auth = subparsers.add_parser("auth", help="管理 BOSS Cookie")
    auth_commands = auth.add_subparsers(dest="auth_command", required=True)
    auth_import = auth_commands.add_parser("import", help="安全导入 Cookie JSON")
    auth_import.add_argument("source")
    auth_commands.add_parser("check", help="执行最小登录检查")
    config = subparsers.add_parser("config", help="查看配置")
    config_commands = config.add_subparsers(dest="config_command", required=True)
    config_commands.add_parser("show", help="显示生效配置")
    web = subparsers.add_parser("web", help="启动只读 Web 页面")
    web.add_argument("--host")
    web.add_argument("--port", type=int)
    return parser


def main(argv: Sequence[str] | None = None):
    args = build_parser().parse_args(argv)
    if args.command == "collect":
        import requests

        from auto_seeker.application.collect_jobs import collect_jobs
        from auto_seeker.auth import load_cookie_file
        from auto_seeker.config import PROJECT_ROOT, load_config
        from auto_seeker.infrastructure.boss_client import BossClient
        from auto_seeker.infrastructure.sqlite_repository import SQLiteJobRepository
        from auto_seeker.infrastructure.stoken import StokenService
        from auto_seeker.models import SearchCriteria

        config = load_config(
            args.config,
            {
                "search.keyword": args.keyword,
                "search.city_code": args.city_code,
                "search.page_count": args.page_count,
            },
        )
        cookie_path = config.runtime.cookie_file
        if not cookie_path.is_absolute():
            cookie_path = PROJECT_ROOT / cookie_path
        cookies = load_cookie_file(
            cookie_path,
            PROJECT_ROOT / "cookies.json",
            cookie_path.with_suffix(".txt"),
            PROJECT_ROOT / "cookies.txt",
        )
        session = requests.Session()
        session.cookies.update(cookies)
        criteria = SearchCriteria(
            config.search.keyword,
            config.search.city_code,
            config.search.minimum_salary_k,
            config.search.maximum_experience_years,
        )
        client = BossClient(session, criteria, config.search.page_size, config.request.timeout_seconds)
        cache_dir = config.runtime.cache_dir
        database_path = config.storage.database
        if not cache_dir.is_absolute():
            cache_dir = PROJECT_ROOT / cache_dir
        if not database_path.is_absolute():
            database_path = PROJECT_ROOT / database_path
        stoken = StokenService(session, client.page_url, cache_dir, client.user_agent, client.timeout)
        repository = SQLiteJobRepository(database_path)
        result = collect_jobs(
            client,
            stoken,
            repository,
            criteria,
            config.search.start_page,
            config.search.page_count,
            config.request.interval_seconds,
        )
        print(
            f"采集完成：批次={result.run_id} 符合条件={result.matched_count} "
            f"新增={result.new_count} SQLite={database_path}"
        )
        return 0
    if args.command == "auth":
        from auto_seeker.auth import check_cookies, import_cookies
        from auto_seeker.config import PROJECT_ROOT, load_config

        config = load_config(args.config)
        cookie_path = config.runtime.cookie_file
        if not cookie_path.is_absolute():
            cookie_path = PROJECT_ROOT / cookie_path
        if args.auth_command == "import":
            count = import_cookies(args.source, cookie_path)
            print(f"已安全导入 {count} 个 BOSS Cookie：{cookie_path}")
            return 0
        payload = json.loads(cookie_path.read_text(encoding="utf-8"))
        code = check_cookies(payload, timeout=config.request.timeout_seconds)
        print(f"BOSS 登录检查成功，业务码={code}")
        return 0
    if args.command == "web":
        import uvicorn

        from auto_seeker.config import PROJECT_ROOT, load_config
        from auto_seeker.web.app import create_app

        config = load_config(
            args.config,
            {
                "web.host": args.host,
                "web.port": args.port,
            },
        )
        database_path = config.storage.database
        if not database_path.is_absolute():
            database_path = PROJECT_ROOT / database_path
        app = create_app(database_path)
        uvicorn.run(app, host=config.web.host, port=config.web.port)
        return 0
    if args.command == "config" and args.config_command == "show":
        from dataclasses import asdict

        from auto_seeker.config import load_config

        payload = asdict(load_config(args.config))
        payload["runtime"]["cookie_file"] = "<redacted-path>"
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
