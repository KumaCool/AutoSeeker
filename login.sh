#!/bin/zsh
set -eu

ROOT="${0:A:h}"
cd "$ROOT"

if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "缺少 .venv，请先运行 ./setup.sh" >&2
  exit 1
fi

"$ROOT/.venv/bin/python" "$ROOT/browser_auth.py" --timeout 300
SKIP_BROWSER_AUTH=1 "$ROOT/run_daily.sh"
