#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

if ! command -v uv >/dev/null 2>&1; then
  echo "缺少 uv：https://docs.astral.sh/uv/" >&2
  exit 1
fi

UV_HTTP_TIMEOUT="${UV_HTTP_TIMEOUT:-120}" UV_HTTP_RETRIES="${UV_HTTP_RETRIES:-5}" uv sync --locked
mkdir -p var/secrets var/cache/security-js var/logs var/outputs
chmod +x scripts/setup.sh scripts/run-daily.sh scripts/macos/login.sh scripts/macos/install-launchd.sh
echo "环境已创建。请使用 autoseeker auth import 导入 Cookie；macOS 可运行 scripts/macos/login.sh。"
