import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from boss_zhipin import __version__


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
        import boss_jobs
        from boss_zhipin.config import load_config

        config = load_config(
            args.config,
            {
                "search.keyword": args.keyword,
                "search.city_code": args.city_code,
                "search.page_count": args.page_count,
            },
        )
        boss_jobs.apply_config(config)

        boss_jobs.main()
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
