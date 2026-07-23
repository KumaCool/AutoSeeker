#!/bin/zsh
set -eu

ROOT="${0:A:h}"
cd "$ROOT"

if ! command -v uv >/dev/null 2>&1; then
  echo "缺少 uv，请先安装：https://docs.astral.sh/uv/" >&2
  exit 1
fi

export UV_HTTP_TIMEOUT="${UV_HTTP_TIMEOUT:-120}"
export UV_HTTP_RETRIES="${UV_HTTP_RETRIES:-5}"
uv sync --index-url https://pypi.org/simple

mkdir -p var/secrets var/cache/security-js var/logs var/outputs

if [[ ! -f var/secrets/cookies.json ]]; then
  if [[ -f cookies.json ]]; then
    install -m 600 cookies.json var/secrets/cookies.json
  else
    install -m 600 cookies.example.json var/secrets/cookies.json
  fi
fi

chmod +x login.sh run_daily.sh install_launchd.sh
echo "环境已创建。首次使用请运行 ./login.sh 并扫码登录。"
