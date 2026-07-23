import argparse
import json
import sys
from collections.abc import Sequence

from boss_zhipin import __version__


def ensure_legacy_import_path():
    from boss_zhipin.config import PROJECT_ROOT

    root = str(PROJECT_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def build_parser():
    parser = argparse.ArgumentParser(prog="boss-zhipin", description="BOSS 直聘职位筛选工具")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--config", help="TOML 配置文件路径")
    subparsers = parser.add_subparsers(dest="command", required=True)
    collect = subparsers.add_parser("collect", help="采集职位并增量写入 Excel")
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
    return parser


def main(argv: Sequence[str] | None = None):
    args = build_parser().parse_args(argv)
    if args.command == "collect":
        ensure_legacy_import_path()
        import requests

        import boss_jobs
        from boss_zhipin.application.collect_jobs import collect_jobs
        from boss_zhipin.config import PROJECT_ROOT, load_config
        from boss_zhipin.infrastructure.boss_client import BossClient
        from boss_zhipin.infrastructure.excel_repository import ExcelJobRepository
        from boss_zhipin.infrastructure.stoken import StokenService
        from boss_zhipin.models import SearchCriteria

        config = load_config(
            args.config,
            {
                "search.keyword": args.keyword,
                "search.city_code": args.city_code,
                "search.page_count": args.page_count,
            },
        )
        boss_jobs.apply_config(config)
        cookies = boss_jobs.load_cookies()
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
        output_path = config.output.path
        if not cache_dir.is_absolute():
            cache_dir = PROJECT_ROOT / cache_dir
        if not output_path.is_absolute():
            output_path = PROJECT_ROOT / output_path
        stoken = StokenService(session, client.page_url, cache_dir, client.user_agent, client.timeout)
        repository = ExcelJobRepository(output_path, PROJECT_ROOT / "outputs/wuhan-frontend-jobs.xlsx")
        result = collect_jobs(
            client,
            stoken,
            repository,
            criteria,
            config.search.start_page,
            config.search.page_count,
            config.request.interval_seconds,
        )
        print(f"保存完成：符合条件={result.matched_count} 新增={result.new_count} Excel={output_path}")
        return 0
    if args.command == "auth":
        from boss_zhipin.auth import check_cookies, import_cookies
        from boss_zhipin.config import PROJECT_ROOT, load_config

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
    if args.command == "config" and args.config_command == "show":
        from dataclasses import asdict

        from boss_zhipin.config import load_config

        payload = asdict(load_config(args.config))
        payload["runtime"]["cookie_file"] = "<redacted-path>"
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
