#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"

if ! command -v uv >/dev/null 2>&1; then
  echo "缺少 uv：https://docs.astral.sh/uv/" >&2
  exit 1
fi

UV_HTTP_TIMEOUT="${UV_HTTP_TIMEOUT:-120}" UV_HTTP_RETRIES="${UV_HTTP_RETRIES:-5}" uv sync --locked
mkdir -p var/secrets var/cache/security-js var/logs var/outputs
if [ ! -f var/secrets/cookies.json ]; then
  if [ -f cookies.json ]; then
    install -m 600 cookies.json var/secrets/cookies.json
  else
    install -m 600 cookies.example.json var/secrets/cookies.json
  fi
fi
chmod +x setup.sh run_daily.sh login.sh install_launchd.sh
echo "环境已创建。Linux 可用 boss-zhipin auth import 导入 Cookie；macOS 可运行 ./login.sh。"
