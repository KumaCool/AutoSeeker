import argparse
from collections.abc import Sequence

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
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
