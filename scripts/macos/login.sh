#!/bin/zsh
set -eu

ROOT="${0:A:h:h:h}"
cd "$ROOT"

if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "缺少 .venv，请先运行 scripts/setup.sh" >&2
  exit 1
fi

BOSS_PROJECT_ROOT="$ROOT" "$ROOT/.venv/bin/python" -m boss_zhipin.browser_auth --timeout 300
"$ROOT/scripts/run-daily.sh"
