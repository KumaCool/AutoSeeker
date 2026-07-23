import argparse
from collections.abc import Sequence

from boss_zhipin import __version__


def build_parser():
    parser = argparse.ArgumentParser(prog="boss-zhipin", description="BOSS 直聘职位筛选工具")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("collect", help="采集职位并增量写入 Excel")
    return parser


def main(argv: Sequence[str] | None = None):
    args = build_parser().parse_args(argv)
    if args.command == "collect":
        import boss_jobs

        boss_jobs.main()
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
